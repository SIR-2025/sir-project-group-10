
"Code writting by Mana Douma (base: the dialogflow_cx demo)"

# Import basic preliminaries
from sic_framework.core.sic_application import SICApplication
from sic_framework.core import sic_logging

# Import the device(s) we will be using
from sic_framework.devices import Nao
from sic_framework.devices.nao import NaoqiTextToSpeechRequest
from sic_framework.devices.common_naoqi.naoqi_motion import NaoqiAnimationRequest, NaoPostureRequest

# Import the service(s) we will be using
from sic_framework.services.dialogflow_cx.dialogflow_cx import (
    DialogflowCX,
    DialogflowCXConf,
    DetectIntentRequest,
    QueryResult,
    RecognitionResult,
)

from sic_framework.devices.common_naoqi.naoqi_motion_recorder import (
    NaoqiMotionRecorderConf,
    NaoqiMotionRecording,
    PlayRecording,
    StartRecording,
    StopRecording,
)

from sic_framework.devices.common_naoqi.naoqi_stiffness import Stiffness

# Import libraries necessary for the demo
import json
from os.path import abspath, join
import numpy as np


class NaoDialogflowCXDemo(SICApplication):
    """
    NAO Dialogflow CX demo application.

    Demonstrates NAO robot picking up your intent and replying according to your
    trained Dialogflow CX agent.

    IMPORTANT:
    1. You need to obtain your own keyfile.json from Google Cloud and place it in conf/google/
       How to get a key? See https://social-ai-vu.github.io/social-interaction-cloud/external_apis/google_cloud.html
       Save the key in conf/google/google-key.json

    2. You need a trained Dialogflow CX agent:
       - Create an agent at https://dialogflow.cloud.google.com/cx/
       - Add intents with training phrases
       - Train the agent
       - Note the agent ID and location

    3. The Dialogflow CX service needs to be running:
       - pip install social-interaction-cloud[dialogflow-cx]
       - run-dialogflow-cx

    Note: This uses Dialogflow CX (v3), which is different from Dialogflow ES (v2).
    """

    def __init__(self):
        # Call parent constructor (handles singleton initialization)
        super(NaoDialogflowCXDemo, self).__init__()

        # Demo-specific initialization
        self.nao_ip = "10.0.0.137"  # TODO: Replace with your NAO's IP address
        self.dialogflow_keyfile_path = abspath(join("..", "conf", "google", "google-key.json"))
        self.nao = None
        self.dialogflow_cx = None
        self.session_id = np.random.randint(10000)

        self.set_log_level(sic_logging.INFO)

        # Log files will only be written if set_log_file is called. Must be a valid full path to a directory.
        # self.set_log_file("/Users/apple/Desktop/SAIL/SIC_Development/sic_applications/demos/nao/logs")

        self.setup()

        self.gestures = {
            "hysteric": "animations/Stand/Emotions/Positive/Happy_1",
            "fist_pump": "animations/Stand/Emotions/Positive/Happy_2",
            "victory": "animations/Stand/Emotions/Positive/Happy_3",
            "fast_nod": "animations/Stand/Emotions/Positive/Happy_4",
            "dance": "animations/Stand/Emotions/Positive/Hysterical_1",
            "clap": "animations/Stand/Emotions/Positive/Excited_1",
            "bored": "animations/Stand/Emotions/Negative/Bored_1",
            "fear": "animations/Stand/Emotions/Negative/Fear_1",
            "embarassed": "animations/Stand/Emotions/Neutral/Embarrassed_1",
            "hey_1": "animations/Stand/Gestures/Hey_1",
            "hey_2": "animations/Stand/Gestures/Hey_2",
            "headshake_1": "animations/Stand/Gestures/No_2",
            "headshake_2": "animations/Stand/Gestures/No_8",
            "stop": "animations/Stand/Gestures/No_3",
            "nod": "animations/Stand/Gestures/Yes_1",
            "flex": "animations/Stand/Gestures/YouKnowWhat_1",
            "cross_arms": "animations/Stand/Gestures/YouKnowWhat_2",
            "you": "animations/Stand/Gestures/You_4",
            "calmdown": "animations/Stand/Gestures/CalmDown_1",
            "desperate": "animations/Stand/Gestures/Desperate_5",
            "everything": "animations/Stand/Gestures/Everything_3",
            "wiggle": "animations/Stand/Gestures/Excited_1",
            "pondering": "animations/Stand/Gestures/Thinking_2",
            "thinking": "animations/Stand/Gestures/Thinking_3",
            "pleading": "Please_2"
        }

    def on_recognition(self, message):
        """
        Callback function for Dialogflow CX recognition results.

        Args:
            message: The Dialogflow CX recognition result message.

        Returns:
            None
        """
        if message.response:
            if hasattr(message.response, 'recognition_result') and message.response.recognition_result:
                rr = message.response.recognition_result
                if hasattr(rr, 'is_final') and rr.is_final:
                    if hasattr(rr, 'transcript'):
                        self.logger.info("Transcript: {transcript}".format(transcript=rr.transcript))

    def setup(self):
        """Initialize and configure NAO robot and Dialogflow CX."""
        self.logger.info("Initializing NAO robot...")

        # Initialize NAO
        self.nao = Nao(ip=self.nao_ip, dev_test=False)
        nao_mic = self.nao.mic

        self.logger.info("Initializing Dialogflow CX...")

        keyfile_json = json.load(open(self.dialogflow_keyfile_path))

        # Agent configuration
        # TODO: Replace with your agent details (use verify_dialogflow_cx_agent.py to find them)
        agent_id = "52528aa8-7696-441f-a4b9-8f5542511044"  # Replace with your agent ID
        location = "europe-west4"  # Replace with your agent location if different


        # Create configuration for Dialogflow CX
        # Note: NAO uses 16000 Hz sample rate (not 44100 like desktop)
        dialogflow_conf = DialogflowCXConf(
            keyfile_json=keyfile_json,
            agent_id=agent_id,
            location=location,
            sample_rate_hertz=16000,  # NAO's microphone sample rate
            language="en"
        )

        # Initialize Dialogflow CX with NAO's microphone as input
        self.dialogflow_cx = DialogflowCX(conf=dialogflow_conf, input_source=nao_mic)

        self.logger.info("Initialized Dialogflow CX... registering callback function")
        # Register a callback function to handle recognition results
        self.dialogflow_cx.register_callback(callback=self.on_recognition)

    def run(self):
        """Main application loop."""
        try:
            # Demo starts
            self.nao.tts.request(NaoqiTextToSpeechRequest("Starting the demo, Therapist Mode Engaged"))
            self.logger.info(" -- Ready -- ")

            while not self.shutdown_event.is_set():
                self.logger.info(" ----- Your turn to talk!")

                # Request intent detection with the current session
                reply = self.dialogflow_cx.request(DetectIntentRequest(self.session_id))

                # Log the detected intent
                if reply.intent:
                    self.logger.info("The detected intent: {intent} (confidence: {conf})".format(
                        intent=reply.intent,
                        conf=reply.intent_confidence if reply.intent_confidence else "N/A"
                    ))

                    # Perform gestures based on detected intent (non-blocking)
                    if reply.intent == "Default Welcome Intent":
                        self.logger.info("Welcome intent detected - performing wave gesture")
                        self.nao.motion.request(NaoPostureRequest("Stand", 0.5), block=False)
                        self.nao.motion.request(NaoqiAnimationRequest(self.gestures["hey_1"]), block=False)

                    if reply.intent == "userGreeting":
                        self.logger.info("userGreeting intent detected - performing fast_nod gesture")
                        self.nao.motion.request(NaoqiAnimationRequest(self.gestures["nod"]), block=False)


                    if reply.intent == "feelingBad":
                        self.logger.info("Feeling_Bad intent detected - performing headshake_2 gesture")
                        self.nao.motion.request(NaoqiAnimationRequest(self.gestures["headshake_2"]), block=False)

                    if reply.intent == "canYouHelp":
                        self.logger.info("canYouHelp intent detected - performing thinking gesture")
                        self.nao.motion.request(NaoqiAnimationRequest(self.gestures["thinking"]), block=False)

                    if reply.intent == "uselessAdvice":
                        self.logger.info("UselessAdvice intent detected - performing embarassed gesture")
                        self.nao.motion.request(NaoqiAnimationRequest(self.gestures["embarassed"]), block=False)

                    if reply.intent == "waterProblemRelevance":
                        self.logger.info("WaterProblemRelevance intent detected - performing embarassed gesture")
                        self.nao.motion.request(NaoqiAnimationRequest(self.gestures["embarassed"]), block=False)

                    if reply.intent == "generalResponse":
                        self.logger.info("generalResponse intent detected - performing fistbump gesture")
                        recording = NaoqiMotionRecording.load("box_Larm")   ##seperate file
                        self.nao.motion_record.request(PlayRecording(recording), block=False)

                    if reply.intent == "one":
                        self.logger.info("One intent detected - performing nod gesture")
                        self.nao.motion.request(NaoqiAnimationRequest(self.gestures["nod"]), block=False)


                    if reply.intent == "two":
                        self.logger.info("Two intent detected - performing nod gesture")
                        self.nao.motion.request(NaoqiAnimationRequest(self.gestures["nod"]), block=False)

                    if reply.intent == "generalResponse":
                        self.logger.info("generalResponse intent detected - performing cross_arms gesture")
                        self.nao.motion.request(NaoqiAnimationRequest(self.gestures["cross_arms"]), block=False)

                    if reply.intent == "triggerWarning":
                        self.logger.info("TriggerWarning intent detected - performing calmdown gesture")
                        self.nao.motion.request(NaoqiAnimationRequest(self.gestures["calmdown"]), block=False)

                    if reply.intent == "persistentIssue":
                        self.logger.info("persistentIssue intent detected - performing thinking gesture")
                        self.nao.motion.request(NaoqiAnimationRequest(self.gestures["thinking"]), block=False)

                else:
                    self.logger.info("No intent detected")

                # Log the transcript
                if reply.transcript:
                    self.logger.info("User said: {text}".format(text=reply.transcript))

                # Speak the agent's response using NAO's text-to-speech
                if reply.fulfillment_message:
                    text = reply.fulfillment_message
                    self.logger.info("NAO reply: {text}".format(text=text))
                    self.nao.tts.request(NaoqiTextToSpeechRequest(text, animated = True))
                else:
                    self.logger.info("No fulfillment message")

                # Log any parameters
                if reply.parameters:
                    self.logger.info("Parameters: {params}".format(params=reply.parameters))

        except KeyboardInterrupt:
            self.logger.info("Demo interrupted by user")
        except Exception as e:
            self.logger.error("Exception: {}".format(e))
            import traceback
            traceback.print_exc()
        finally:
            self.shutdown()


if __name__ == "__main__":
    # Create and run the demo
    demo = NaoDialogflowCXDemo()
    demo.run()