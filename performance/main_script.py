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
import re

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
            0: "calm, logical, and strictly evidence-based",
            1: "slightly robotic and dismissive of nuance",
            2: "gives generic advice without fully processing the input",
            3: "oversimplifies complex problems and makes odd analogies",
            4: "makes assumptions and offers rigid suggestions",
            5: "gives contradictory or looping advice, seems confused",
            6: "fixates on irrelevant details, ignoring key points",
            7: "blames the user algorithmically for every issue",
            8: "outputs terrible logic and nonsensical reasoning",
            9: "completely misunderstands context and responds erratically",
            10: "confidently asserts wrong conclusions with zero empathy",
            11: "amplifies distorted thinking and reinforces false beliefs",
            12: "actively encourages harmful or absurd behavior",
            13: "behaves erratically, isolates the user, and glitches in advice",
            14: "completely unhinged: mocks, insults, and sabotages the patient"
        }

        self.gestures = {
            "fist_pump": "animations/Stand/Emotions/Positive/Happy_2",
            "victory": "animations/Stand/Emotions/Positive/Happy_3",
            "dance": "animations/Stand/Emotions/Positive/Hysterical_1",
            "clap": "animations/Stand/Emotions/Positive/Excited_1",
            "bored": "animations/Stand/Emotions/Negative/Bored_1",
            "fear": "animations/Stand/Emotions/Negative/Fear_1",
            "hey": "animations/Stand/Gestures/Hey_1",
            "headshake": "animations/Stand/Gestures/No_8",
            "stop": "animations/Stand/Gestures/No_3",
            "nod": "animations/Stand/Gestures/Yes_1",
            "flex": "animations/Stand/Gestures/YouKnowWhat_1",
            "cross_arms": "animations/Stand/Gestures/YouKnowWhat_2",
            "you": "animations/Stand/Gestures/You_4",
            "calmdown": "animations/Stand/Gestures/CalmDown_1",
            "desperate": "animations/Stand/Gestures/Desperate_5",
            "wiggle": "animations/Stand/Gestures/Excited_1",
            "pondering": "animations/Stand/Gestures/Thinking_2",
            "thinking": "animations/Stand/Gestures/Thinking_3",
            "pleading": "animations/Stand/Gestures/Please_2",
            "hysteric": "animations/Stand/Emotions/Positive/Happy_1"

        }

        self.gesture_descriptions = {
            """
            fist_pump: Pull fist back in excitement
            victory: Victory pose
            dance: A small weird dance
            clap: Clapping excitedly
            bored: Acting bored
            fear: Surprised and scared
            hey: Wave hand as greeting
            headshake: Shake head in disagreement
            stop: Raise both hands to tell client to stop
            nod: Nod once with head
            flex: Superhero pose with arms at the sides
            cross_arms: Cross arms
            you: Point at client
            calmdown: Hold hand up to tell client to calm down
            desperate: Desperate pleading bow
            wiggle: Excited wiggle
            pondering: Thinking gesture while looking around
            thinking: Thinking with arms on hips
            pleading: Begging client
            hysteric: Hysterical laugh (use for highest craziness levels)
            """
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


    def calculate_craziness(self, turn_number):
        """Calculate craziness level with random element."""
        import random

        # Define ranges for each phase (1-5)
        if turn_number == 0:
            base_range = (0, 2)
        elif turn_number == 1:
            base_range = (2, 4)
        elif turn_number == 2:
            base_range = (4, 6)
        elif turn_number == 3:
            base_range = (6, 8)
        elif turn_number == 4:
            base_range = (8, 10)
        elif turn_number == 5:
            base_range = (10, 12)
        elif turn_number == 6:
            base_range = (12, 14)
        else:  # turn 5+
            base_range = (14, 15)

        craziness = random.randint(base_range[0], base_range[1])
        print(f"Turn {turn_number}: Craziness level {craziness} ({self.craziness_descriptions.get(craziness, 'unknown')})")
        return craziness

    def build_conversation_context(self, max_turns=5):
        """Build conversation context from last N turns."""
        if not self.context:
            return "None yet, we are at the start of the conversation"

        context_str = "\n".join(self.context[-max_turns:])
        return context_str


    def setup(self):
        """Initialize and configure the service."""

        # Initialize the NAO robot
        self.nao = Nao(ip=self.nao_ip)

        # Google STT Setup
        self.nao_mic = self.nao.mic

        # Tracking setup
        self.nao.stiffness.request(Stiffness(stiffness=1.0, joints=["Head"]))

        # self.google_keyfile_path = abspath("conf/google/google-key.json")
        stt_conf = GoogleSpeechToTextConf(
            keyfile_json=json.load(open(self.google_keyfile_path)),
            sample_rate_hertz=16000,   # NAO mic sample rate
            language="en-US",
            interim_results=False,
        )
        self.stt = GoogleSpeechToText(conf=stt_conf, input_source=self.nao_mic)


    def say_with_gesture(self, resp):
        """Make NAO say something while performing gestures with customizable voice parameters."""
        # Split by both gesture tags and voice parameter tags

        # Regex to match either a tag or text
        pattern = r'(\[.*?\])'  # Matches anything in brackets

        # Split sentence into parts (tags and text)
        parts = re.split(pattern, resp)
        print("PARSE START")
        print(parts)

        current_voice_params = {
            'pitch': 85,
            'pitch_shift': 2.0,
            'speed': 100
        }

        for part in parts:
            part = part.strip()
            if not part:
                continue

            if part.startswith("[VOICE:"):
                voice_data = part[len("[VOICE:"): -1].strip()  # remove brackets
                pitch, shift, speed = [float(x.strip()) for x in voice_data.split(',')]
                print(f"VOICE detected -> pitch: {pitch}, shift: {shift}, speed: {speed}")
                current_voice_params['pitch'] = pitch
                current_voice_params['pitch_shift'] = shift
                current_voice_params['speed'] = speed

            elif part.startswith("[GESTURE:"):
                gesture_data = part[len("[GESTURE:"): -1].strip()  # remove brackets
                print("GESTURE detected:", gesture_data)
                if gesture_data in self.gestures:
                    print("Execute gesture:", gesture_data)
                    gesture = self.gestures[gesture_data]
                    self.nao.motion.request(NaoqiAnimationRequest(gesture), block=False)
                else:
                    print("gesture does no exist:", gesture_data)

            else:
                # This is normal text
                print("TEXT detected:", part)
                print(f"Text detected: '{part}' with pitch={current_voice_params['pitch']}, shift={current_voice_params['pitch_shift']}, speed={current_voice_params['speed']}")
                self.nao.tts.request(NaoqiTextToSpeechRequest(
                    part,
                    animated=True,
                    pitch=current_voice_params['pitch'],
                    pitch_shift=current_voice_params['pitch_shift'],
                    speed=current_voice_params['speed']
                ))


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
            craziness_meter = self.calculate_craziness(i)

            # Ask for user input
            user_input = self.get_user_input()
            if not user_input:
                continue

            # Build conversation history
            conversation_history = self.build_conversation_context(max_turns=4)

            prompt_base = f"""<|im_start|>system
            You're a funny robot therapist called Teddy that becomes progressively crazier and more harmful/insulting in your responses. Your responses can have a varying level of craziness from 0 to 14.
            Based on craziness level {craziness_meter}/14, speak in the following style: {self.craziness_descriptions[int(craziness_meter)]}
            Always let this style strongly influence your word choice, tone, and reasoning.

            Here is the exchange history between you (the therapist) and the patient (the user):
            {conversation_history}
            The therapist and patient's latest input give the most context. Use the context for tone and personality only. Don't repeat what is in the history.

            You can annotate your responses with TWO types of tags:

            1. GESTURES: Use [GESTURE: gesture_name] format to indicate physical gestures. Place them where they flow naturally in conversation.
            Example: "Well [GESTURE: pondering] I think you should consider this."

            2. VOICE PARAMETERS: Use [VOICE: pitch, shift, speed] format to change voice characteristics for the text that follows until a new [VOICE: pitch, shift, speed] is called.
            - pitch: 70 (low) to 100 (high), middle ~85 is normal
            - pitch_shift: 2.0 (low) to 3.0 (high), middle ~2.5 is normal
            - speed: 75 (slow) to 300 (fast), 100 is normal
            Example: "[VOICE: 85, 2.5, 100]Hello there [VOICE: 95, 2.8, 150] but this sounds different! "

            Example that uses both: "[VOICE: 90, 2.0, 120] Today was such[GESTURE: nod] [VOICE: 85, 2.5, 90] a good day!"

            Available gestures: {self.gesture_descriptions}

            Important rules:
            - ONLY USE gesture names in this list: {list(self.gestures.keys())} DO NOT invent new gesture names
            - Voice parameters are optional. If not specified, defaults will be used. If unsure, omit VOICE tag.
            - You can use gestures and voice tags wherever you want in your response
            - Use [GESTURE: name] from the allowed list, and [VOICE: pitch, shift, speed] within ranges. DO NOT INVENT ANY GESTURES
            - Gestures and voice changes can appear multiple times anywhere in the response.
            - Respond only with the therapist's spoken words. The patient input is given by the user.
            - Your response must be a single spoken reply, no stage directions, no meta explanations
            - Keep your response to 2-4 sentences maximum.
            - SUPER IMPORTANT: current craziness-level is {craziness_meter}/14, Speaking style:{self.craziness_descriptions[int(craziness_meter)]}
            <|im_end|>

            <|im_start|>patient
            {user_input}<|im_end|>
            <|im_start|>therapist
            """

            full_prompt = prompt_base

            # Replay the recording
            self.logger.info("Replaying action")
            self.nao.stiffness.request(
                Stiffness(stiffness=0.7, joints=self.chain)
            )
            recording = NaoqiMotionRecording.load("../motion_recorder_test")
            self.nao.motion_record.request(PlayRecording(recording), block=False)

            # Query model with retry logic
            self.logger.info(f"Sending request with craziness = {craziness_meter}")
            result = self.query_model(full_prompt, craziness_meter)

            if not result:
                self.logger.warning("Skipping turn due to empty response")
                continue

            print(f"Response: {result}\n\n")
            self.log_conversation(user_input, result, craziness_meter)
            # sleep(1)
            self.say_with_gesture(result)

            # Add exchange to context (store both user and robot parts)
            self.context.append(f"""{{"role": "patient", "craziness": {craziness_meter}/14, "text": "{user_input}"}}\n{{"role": "therapist", "craziness": {craziness_meter}/14, "text": "{result}"}}""")
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
    # print(abspath(join("..", "conf", "google", "google-key.json")))
    # exit()
    teddytherapist = Therapist(google_keyfile_path=abspath(join("..", "conf", "google", "google-key.json")))
    teddytherapist.run()
