# Import basic preliminaries
from sic_framework.core.sic_application import SICApplication
from sic_framework.core import sic_logging

# STT imports
from sic_framework.services.google_stt.google_stt import (
    GoogleSpeechToText,
    GoogleSpeechToTextConf,
    GetStatementRequest,
)

# Import message types and requests required for custom motions
from sic_framework.devices.common_naoqi.naoqi_motion_recorder import (
    NaoqiMotionRecorderConf,
    NaoqiMotionRecording,
    PlayRecording,
    StartRecording,
    StopRecording,
)

from sic_framework.devices.common_naoqi.naoqi_stiffness import Stiffness

# Import the device(s) we will be using
from sic_framework.devices import Nao
from sic_framework.devices.nao_stub import NaoStub

# Import message types and requests
from sic_framework.devices.common_naoqi.naoqi_autonomous import NaoWakeUpRequest, NaoRestRequest
from sic_framework.devices.common_naoqi.naoqi_motion import NaoqiAnimationRequest
from sic_framework.devices.common_naoqi.naoqi_text_to_speech import (
    NaoqiTextToSpeechRequest,
)
from sic_framework.devices.common_naoqi.naoqi_stiffness import Stiffness
from sic_framework.devices.common_naoqi.naoqi_tracker import (
    RemoveTargetRequest,
    StartTrackRequest,
    StopAllTrackRequest,
)

# Import needed libraries
from time import sleep
import json
import requests
import os
from datetime import datetime
from os.path import abspath, join

class Therapist(SICApplication):
    """
    Our main code execution which requires a backend LLM to be running. We use colab to achieve this.
    """

    def __init__(self, google_keyfile_path):
        # Call parent constructor (handles singleton initialization)
        super(Therapist, self).__init__()

        self.context = []
        self.NUM_TURNS_part1 = 13
        self.chain = ["LArm", "RArm"]

        # Nao initialization
        self.nao_ip = "10.0.0.137"
        self.nao = None

        # STT Initialization
        self.nao_mic = None
        self.google_keyfile_path = google_keyfile_path
        self.stt = None

        # Colab API setup
        self.API_URL = "https://sociopolitical-blanketlike-preston.ngrok-free.dev/generate"


        # Configure logging
        self.set_log_level(sic_logging.INFO)

        self.setup()

        self.craziness_descriptions = {
            0: "professional and evidence-based",
            1: "slightly dismissive", 
            2: "gives generic advice without listening",
            3: "oversimplifies complex problems",
            4: "makes assumptions without asking questions",
            5: "gives contradictory advice",
            6: "focuses on irrelevant details",
            7: "blames the user for everything",
            8: "gives terrible logical fallacies as advice",
            9: "completely misunderstands the problem",
            10: "gives confidently wrong advice with zero empathy",
            11: "agrees with distorted thinking",
            12: "actively reinforces harmful beliefs",
            13: "encourages isolation and self-destructive behavior",
            14: "openly mocks and insults the patient while giving horrible advice"
        }

    def setup_chat_logging(self):
        """Create chats directory and determine next chat file number."""
        # Create chats directory if it doesn't exist
        if not os.path.exists("chats"):
            os.makedirs("chats")
    
        # Find the next available chat number
        existing_chats = [f for f in os.listdir("chats") if f.endswith(".txt")]
        if not existing_chats:
            self.chat_number = 1
        else:
            numbers = [int(f.split(".")[0]) for f in existing_chats if f.split(".")[0].isdigit()]
            self.chat_number = max(numbers) + 1 if numbers else 1
        
        self.chat_file = f"chats/{self.chat_number}.txt"
        self.logger.info(f"Logging conversation to {self.chat_file}")

    def log_conversation(self, user_input, robot_response, craziness_level):
        """Log a conversation turn to the chat file."""
        with open(self.chat_file, "a") as f:
            f.write(f"Craziness Level: {craziness_level}\n")
            f.write(f"User: {user_input}\n")
            f.write(f"Robot: {robot_response}\n")
            f.write("-" * 60 + "\n\n")

    def clean_incomplete_sentence(self, text):
        """
        Remove incomplete sentences and unwanted characters from the response.
        Returns cleaned text or None if nothing remains.
        """
        if not text or not text.strip():
            return None
        
        text = text.strip()
        
        # Remove leading and trailing quotation marks which result in pronunciation errors
        text = text.strip('"').strip("'").strip('"').strip('"')
        text = text.strip()
        
        # Check if ends with sentence-ending punctuation
        if text and text[-1] in '.!?':
            return text
        
        # Find the last sentence-ending punctuation
        last_period = text.rfind('.')
        last_exclamation = text.rfind('!')
        last_question = text.rfind('?')
        
        last_sentence_end = max(last_period, last_exclamation, last_question)
        
        # If we found a sentence ending, cut off everything after it
        if last_sentence_end > 0:
            cleaned = text[:last_sentence_end + 1].strip()
            # Remove any trailing quotes from the cleaned text too
            cleaned = cleaned.strip('"').strip("'").strip('"').strip('"')
            print(f"Cleaned incomplete sentence. Original length: {len(text)}, Cleaned: {len(cleaned)}")
            return cleaned
        
        # No complete sentences found (there are no full sentences at all)
        print("No complete sentences found")
        return None


    def query_model(self, prompt, craziness_level, max_retries=3):
        """Query the model with retry logic for empty responses."""
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self.API_URL,
                    json={
                        "prompt": prompt,
                        "craziness": craziness_level
                    },
                    headers={"ngrok-skip-browser-warning": "true"},
                    timeout=30
                )

                print(f"Status: {response.status_code}")

                if response.status_code == 200:
                    generated_text = response.json()['generated_text']
                    
                    print("\nRaw generated text:\n")
                    print(generated_text)
                    cleaned_text = self.clean_incomplete_sentence(generated_text)
                    
                    if cleaned_text and len(cleaned_text) > 10:  # Make sure we have substantial text
                        return cleaned_text
                    else:
                        print(f"Response too short or incomplete on attempt {attempt + 1}, retrying...")
                        continue
                else:
                    print(f"Response: {response.text}")
                    return None
                    
            except Exception as e:
                print(f"Error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    sleep(1)
                    continue
                return None
        
        print("All retry attempts failed, skipping this turn")
        return None


    def calculate_craziness(self, turn_number, total_turns):
        """Calculate craziness level with random element."""
        import random
        
        # Define ranges for each phase (1-5)
        if turn_number == 0:
            base_range = (0, 2)
        elif turn_number == 1:
            base_range = (2, 4)
        elif turn_number == 2:
            base_range = (5, 7)
        elif turn_number == 3:
            base_range = (8, 10)
        elif turn_number == 4:
            base_range = (11, 12)
        else:  # turn 5+
            base_range = (13, 14)
        
        craziness = random.randint(base_range[0], base_range[1])
        print(f"Turn {turn_number}: Craziness level {craziness} ({self.craziness_descriptions.get(craziness, 'unknown')})")
        return craziness

    def build_conversation_context(self, max_turns=5):
        """Build conversation context from last N turns."""
        if not self.context:
            return ""
        
        recent_context = self.context[-max_turns:]
        context_str = "\n".join([f"Previous exchange: {exchange}" for exchange in recent_context])
        return context_str


    def setup(self):
        """Initialize and configure the service."""

        # Initialize the NAO robot
        self.nao = Nao(ip=self.nao_ip)

        # Google STT Setup
        self.nao_mic = self.nao.mic

        # Tracking setup
        self.nao.stiffness.request(Stiffness(stiffness=1.0, joints=["Head"]))

        self.google_keyfile_path = abspath("conf/google/google-key.json")
        stt_conf = GoogleSpeechToTextConf(
            keyfile_json=json.load(open(self.google_keyfile_path)),
            sample_rate_hertz=16000,   # NAO mic sample rate
            language="en-US",
            interim_results=False,
        )
        self.stt = GoogleSpeechToText(conf=stt_conf, input_source=self.nao_mic)


    def say_animated(self):
        """Make NAO say something with animated gestures."""
        self.nao.tts.request(NaoqiTextToSpeechRequest("Animated Say."))
        self.nao.tts.request(NaoqiTextToSpeechRequest("Hello, I am a Nao robot! And I like to chat.", animated=True))


    def say_with_gesture(self, resp):
        """Make NAO say something while performing a gesture."""
        self.nao.tts.request(NaoqiTextToSpeechRequest(resp, animated=True))


    def wakeup(self):
        """Wake up the NAO robot."""
        self.nao.autonomous.request(NaoWakeUpRequest())


    def rest(self):
        """Put the NAO robot to rest."""
        self.nao.autonomous.request(NaoRestRequest())

    def get_user_input(self):
        """Capture speech from the NAO mic and transcribe via Google STT."""
        self.logger.info("Listening for speech...")
        result = self.stt.request(GetStatementRequest())

        if not result or not hasattr(result.response, 'alternatives') or not result.response.alternatives:
            self.logger.warning("No transcript received.")
            return None

        transcript = result.response.alternatives[0].transcript
        print(f"User said: {transcript}")
        return transcript


    def confirm(self, part):
        """
        Awaits user confirmation for the next part
        """
        print("\n"+"="*60+"\n")
        print(f"\tAre we ready for {part}")
        print("\n"+"="*60+"\n")
        answer = None
        while answer != "y" and answer != "yes":
            answer = input("Enter yes/y when ready: ")


    def part1(self):
        """
        Executes part 1 of the performance
        """
        i = 0
        
        while not self.shutdown_event.is_set() and i < self.NUM_TURNS_part1:
            
            # Start tracking a face
            target_name = "Face"
            
            self.logger.info("Enabling head stiffness and starting face tracking...")
            # Enable stiffness so the head joint can be actuated
            self.nao.tracker.request(
                StartTrackRequest(target_name=target_name, size=0.2, mode="Head", effector="None")
            )
            

            # Calculate craziness for this turn
            craziness_meter = self.calculate_craziness(i, self.NUM_TURNS_part1)
            
            # Ask for user input
            user_input = self.get_user_input()
            if not user_input:
                continue

            # Build conversation history
            conversation_history = self.build_conversation_context(max_turns=5)
            
            # Construct full prompt with context
            if conversation_history:
                full_prompt = f"""
                You're a robot therapist that becomes progressively crazier in your responses. Your responses can have a varying level of craziness. In this case, your description is as follows: {self.craziness_descriptions[int(craziness_meter)]}.

    Previous conversation:
    {conversation_history}

    Patient just said: '{user_input}'

    Respond as the therapist. ONLY give your spoken response, no annotations or stage directions."""
            else:
                full_prompt = f"""You're an unhinged therapist. Your responses can have a varying level of craziness. In this case, your description is as follows: {self.craziness_descriptions[int(craziness_meter)]}.

    Patient just said: '{user_input}'

    Respond as the therapist. ONLY give your spoken response, no annotations or stage directions.
    """

            # Replay the recording
            self.logger.info("Replaying action")
            self.nao.stiffness.request(
                Stiffness(stiffness=0.7, joints=self.chain)
            )
            recording = NaoqiMotionRecording.load("motion_recorder_test")
            self.nao.motion_record.request(PlayRecording(recording), block=False)

            # Query model with retry logic
            self.logger.info(f"Sending request with craziness = {craziness_meter}")
            result = self.query_model(full_prompt, craziness_meter)
            
            if not result:
                self.logger.warning("Skipping turn due to empty response")
                continue
            
            print(f"Response: {result}")
            self.log_conversation(user_input, result, craziness_meter)
            sleep(1)
            self.say_with_gesture(result)

            # Add exchange to context (store both user and robot parts)
            self.context.append(f"Patient: {user_input} | Therapist: {result}")
            i += 1


    def part2(self):
        pass


    def run(self):
        """Main application loop."""
        self.logger.info("Starting LLM conversation")

        try:
            self.wakeup()
            self.setup_chat_logging()
            self.logger.info("I am awoken!")
            sleep(1)

            # Get confirmation that we're ready for part1
            self.confirm("Part 1")
            self.part1()

            # Get confirmation that we're ready for part2
            self.confirm("Part 2")
            self.part2()
            self.logger.info("Conversation ended")
            self.rest()

        except Exception as e:
            self.rest()
            self.logger.error("Exception: {}".format(e))
        finally:
            print("Shutting down application\n\n")
            self.rest()
            sleep(2)
            self.shutdown()


if __name__ == "__main__":
    # This will be the single SICApplication instance for the process
    teddytherapist = Therapist(google_keyfile_path=abspath(join("..", "conf", "google", "google-key.json")))
    teddytherapist.run()
