[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/18O6qkbP)
# SIC-SIR Assignment
Group 10

This project aims to show some of the dangers of using robots for therapy. To do this, there are two parts which each show an opposite extreme of robot personality: very safe and mellow, but unable to meaningfully provide information on deep topics, or excessively harsh and unhinged. The message of the final performance is that a good balance between these two extremes must be found before these robots can safely and effectively be deployed as therapists.  


# Execution
### Step 1: Environment
Before being able to run the script, a user will need a sic_venv file as described in the tutorials. Additionally, instructions to run the following demos should be followed as well:
- `demos/desktop/demo_desktop_dialogflow.py`
- `demos/desktop/demo_desktop_google_stt.py`
- `demos/desktop/demo_openai_gpt.py`
- `demos/nao/demo_nao_dialogflow.py`
- `demos/nao/demo_nao_dialogflow_cx.py`
- `demos/nao/demo_nao_motion_recorder.py`
- `demos/nao/nao_openai.py`

Many of the files above contain the same installation processes, but to be sure the project works as expected, we recommend ensuring all of the demos mentioned above run as expected.
NOTE: Some of these demos require personal keys/configurations as well. Naturally, we don't provide our keys in the github, so users should procure their own and set them up according to the demo instructions.

### Step 2: Launch LLM API from Google Colab.
For the second part of the performance, this project makes ues of an uncensored LLM (Nidium's `Llama-3.2-3B-Uncensored`). Using the free version of Google Colab, we set up an API that serves users wanting to do inference using this model. 

The Notebook to host this API endpoint and model is provided in `demos/nao/serveAPI.ipynb`. For ease of access, we recommend uploading it to Colab. To host a publicly available API, we used a free Flask Ngrok server. 
1. Sign up, and find your auth token and the public link the API will be bound to.
2. Paste the authtoken into the final cell of the notebook, in the empty `ngrok.set_auth_token()` call.
3. Ensure that the `self.API_URL` from `demos/nao/serveAPI.py is set to the public link (by default it is set to ours).


### Step 3: Execution
Before running the project, ensure that:
- You are connected via WIFI to the TP-LINK internet.
- Robot 3 is on, is not currently being used, and still has the correct IP address as denoted in `demos/nao/nao_gpt.py` (currently 10.0.0.137).
- The robot is on the ground.

For Linux as well as Windows, simply run `./teddy.sh` from the same directory it is in. For Linux, simply use a terminal to do so, or in Windows, use Git Bash. It will automatically detect your OS type, launch new terminal windows, enter the venv in each of them, and launch the dependencies:
- Redis
- `gpt-run`
- `google-stt-run`
- `nao_gpt.py` (our main script)

If all goes well, after a few seconds the main terminal window will output "Listening to user input". At this point, you can talk to the robot and it will respond using the LLM hosted on Colab.

Regarding the Dialogflow CX script, we are still working on incorporating it in a second file similar to teddy.sh. However, as we were still working out our flow for this section, this has not yet been done. In the following weeks, this will be added. A summary of the current Dialogflow can found in 'Overview Dialogflow.pdf'.
