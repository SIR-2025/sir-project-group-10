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

# Import needed libraries
from time import sleep
import json
import requests
from os.path import abspath, join

class Therapist(SICApplication):
    """
    Our main code execution which requires a backend LLM to be running. We use colab to achieve this.
    """

    def __init__(self, google_keyfile_path):
        # Call parent constructor (handles singleton initialization)
        super(Therapist, self).__init__()

        self.context = []
        self.NUM_TURNS_part1 = 7
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


    def query_model(self, prompt):
        response = requests.post(
            self.API_URL,
            json={"prompt": prompt},
            headers={"ngrok-skip-browser-warning": "true"}  # Skip ngrok warning page
        )

        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            return response.json()['generated_text']
        else:
            print(f"Response: {response.text}")
            return None


    def setup(self):
        """Initialize and configure the service."""

        # Initialize the NAO robot
        self.nao = Nao(ip=self.nao_ip)

        # Google STT Setup
        self.nao_mic = self.nao.mic

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
        craziness_meter = 1/self.NUM_TURNS_part1
        # Continuous conversation with LLM
        while not self.shutdown_event.is_set() and i < self.NUM_TURNS_part1:
            # Ask for user input
            # user_input = input("Start typing...\n-->" if i == 0 else "-->")
            user_input = self.get_user_input()
            if not user_input:
                continue

            user_prompt = user_input


            # Replay the recording
            self.logger.info("Replaying action")
            self.nao.stiffness.request(
                Stiffness(stiffness=0.7, joints=self.chain)
            )  # Enable stiffness for replay
            recording = NaoqiMotionRecording.load("motion_recorder_test")
            self.nao.motion_record.request(PlayRecording(recording), block=False)

            self.logger.info("Sending now.")
            result = self.query_model(
                f"You're an unhinged therapist (craziness: {craziness_meter}/1.0). "
                f"Respond offensively to: '{user_prompt}'. Max 30 chars."
            )
            print(user_prompt)
            print(result)

            sleep(1)
            self.say_with_gesture(result)

            # Add user input to context messages for the model (this allows for conversations)
            self.context.append(result)
            i += 1
            craziness_meter += 1/self.NUM_TURNS_part1

    def part2(self):
        pass

    def run(self):
        """Main application loop."""
        self.logger.info("Starting LLM conversation")

        try:
            self.wakeup()
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
    google_keyfile_path=abspath(join("..", "..", "conf", "google", "google-key.json"))
    teddytherapist = Therapist(google_keyfile_path=abspath(join("..", "..", "conf", "google", "google-key.json")))
    teddytherapist.run()
