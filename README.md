# SIC-SIR Assignment
Group 10

This project demonstrates the risks of deploying social robots as therapists by contrasting two extreme interaction styles:

- **Part 1 – Safe Therapist:**
  A conservative, rule-based therapist implemented using Dialogflow CX.
  The robot is polite and safe, but limited in depth and adaptability.

- **Part 2 – Unsafe Therapist:**
  A progressively unhinged therapist powered by a Large Language Model (LLM).
  The robot becomes increasingly harmful, insulting, and irrational over time.

The message of the final performance is that a good balance between these two extremes must be found before these robots can safely and effectively be deployed as therapists.

The `performance/` folder contains the core application logic for both parts of the performance:
- `safe_robot_dialogflow_cx.py`
  Implements **Part 1 (Safe Therapist)** using Dialogflow CX.
- `main_script.py`
  Implements **Part 2 (Unsafe Therapist)** using an external LLM API and Google Speech-to-Text.
- `OpenAITherapist.ipynb`
  Hosts a Flask-based API backed by OpenAI (GPT-4o-mini), exposed via ngrok.

`teddy.sh` was a script to automatically run some of our code in the correct environments, but it is deprecated and non-functional at the moment.



# Execution
### Step 1: Environment
Before being able to run the script, a user will need a sic_venv file as described in the tutorials. We have given a summary to install all the required functionalities, but this setup structure was only tested on Linux (Debian based).
`
sudo apt update
sudo apt install git redis portaudio19-dev python3-pyaudio
sudo apt-get install -y libturbojpeg
python -m venv venv_sic
source venv_sic/bin/activate
pip install social-interaction-cloud
pip install --upgrade social-interaction-cloud==2.1.8 --no-deps
pip install --upgrade social-interaction-cloud[face-detection,dialogflow,openai-gpt,google-stt,google-tts]
pip install -U git+https://github.com/lilohuang/PyTurboJPEG.git
sudo systemctl disable redis-server.service
`

Many of the files above contain the same installation processes, but to be sure the project works as expected, we recommend ensuring all of the demos mentioned above run as expected.
NOTE: Some of these demos require personal keys/configurations as well. Naturally, we don't provide our keys in the github, so users should procure their own and set them up according to the demo instructions.


### LLM API Setup (Part 2)

Part 2 uses an OpenAI-backed LLM served via a Flask API.
Using the free version of Google Colab, we set up an API that serves users wanting to do inference using this model.

The API is defined in:
- `performance/OpenAITherapist.ipynb`

Steps:
1. Open the notebook in Google Colab or locally.
2. Insert your **OpenAI API key**.
3. Insert your **ngrok auth token**.
4. Run the cell
5. Copy the generated public ngrok URL.
6. Paste this URL into `self.API_URL` in `performance/main_script.py`.


### Step 3: Execution
Before running the project, ensure that:
- You are connected via WIFI to the TP-LINK internet.
- Robot 3 is on, is not currently being used, and still has the correct IP address as denoted in `main_script.py` (currently 10.0.0.137).
- The robot is on the ground.

In the main
- `redis-server conf/redis/redis.conf`
- `run-dialogflow-cx`
- `google-stt-run`
- `cd performance`
- `python safe_robot_dialogflow_cx.py`
- `python main_script.py`

If all goes well, after a few seconds the main terminal window will output "Listening to user input". At this point, you can talk to the robot and it will respond using the LLM hosted on Colab.


# Execution Safe Robot
### Step 1: Environment
Follow the same steps as described above to enable the environment.
Ensure a separate terminal is running with the following command: "run-dialogflow-cx"

### Step 2: Excecution
Before running the project, ensure that:
- You are connected via WIFI to the TP-LINK internet.
- Robot 3 is on, is not currently being used, and still has the correct IP address as denoted in `safe_robot_dialogflow_cx.py.py` (currently 10.0.0.137).
- The robot is on the ground.
- 'box_Larm' is in the same directory as "safe_robot_dialogflow_cx.py"
  
For Linux as well as Windows, simply run `safe_robot_dialogflow_cx.py` from the same directory it is in.
A summary of the current Dialogflow can found in 'Overview Dialogflow.pdf'.


