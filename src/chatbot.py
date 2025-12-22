import os
import sys
import json
import zipfile
import argparse
from pathlib import Path
from datetime import datetime

import PyPDF2
import tiktoken
import streamlit as st
from openai import OpenAI

from pydantic import BaseModel, Field
from langchain.output_parsers import PydanticOutputParser

import config, preprocess_OF_tutorial, main_run_chatcfd, file_preparation
from config import path_cfg, run_cfg, case_info, grid_info  # TODO: 去除config的多余内容
from qa_modules import QA_NoContext_deepseek_R1
from file_summary import get_case_content, generate_case_summary
# import torch
# torch.classes.__path__ = [os.path.join(torch.__path__[0], torch.classes.__file__)] 


# chatbot prompt
SYSTEM_PROMPT = """You are an intelligent assistant capable of:
1. Maintaining politeness and professionalism
2. Remembering the context of the conversation
3. Processing and analyzing content from documents uploaded by users
4. Answering user questions while keeping the conversation coherent

Please always respond in a clear, accurate, and helpful manner
"""

EXTRACT_CASES_FROM_TEXT_PROMPT = """The attached document contain several CFD cases, and I would like to run one or several of the case by my self later. Please read the paper and list all distinct CFD cases with characteristic description. Give each case a tag as Case_X (such as Case_1, Case_2).

- Please count each unique combination of parameters that results in a separate simulation run as one CFD case. These parameters include but not limited to the geometry, boundary Conditions, flow Parameters (Re/Mach/AoA/velocity), physical Model, or Solver.
- If there are multiple runs of the same parameters for statistical analysis or convergence studies, count these as one case, unless the paper specifies them as distinct due to different goals or conditions.
- If any case is simulated using OpenFOAM, identify the solver or find a proper solver to run the case. Show the solver name when describing the case.

The document content is as follows: 
{document_content}.
"""

JSON_RESPONSE_SAMPLE = '''
{
    "Case_1":{
        "case_name":"<some_case_name>",
        "solver":"<solver_name>",
        "turbulence_model":"<model_name>",
        "other_physical_model":"<model_name>",
        "case_specific_description":"<a sentence that describes the case setup with detailed parameters that differenciate this case from the other cases in the paper>"
    }
}
'''

ASK_TO_CHOOSE_CASE_AND_SOLVER = """Please choose the case you want to simulate and the OpenFOAM solver you want to use. 
Your answer shall be like one of the followings:
- I want to simulate Case_1 using rhoCentralFoam and the SpalartAllmaras model.
- I want to simulate the Case with AOA = 10 degree and kOmegaSST model.
        
You must choose only one case.
"""

CONFIRM_SIMULATION_REQUIREMENT = """Next, the CFD simulation will be conducted according to the following settings:
{simulate_requirement}
Do you confirm this simulation setting? If you do, please reply with "yes".
"""

CHOOSE_A_CASE_TO_RUN = """Understand the user's answer and describe the case details of the user's requirement.

    The user's answer is: {user_answer}

    Please generate JSON content according to these requirements:

    1. Strictly follow this example format containing ONLY JSON content: {response_format}

    2. Absolutely AVOID any non-JSON elements including but not limited to:
    - Markdown code block markers (```json or ```)
    - Extra comments or explanations
    - Unnecessary empty lines or indentation
    - Any text outside JSON structure

    3. Critical syntax requirements:
    - Maintain strict JSON syntax compliance
    - Enclose all keys in double quotes
    - Use double quotes for string values
    - Ensure no trailing comma after last property

    4. Case_name must adhere to the following format:
        [a-zA-Z0-9_]+ - only containing lowercase letters, uppercase letters, numbers, or underscores. Special characters (e.g. -, @, #, spaces) are not permitted.

    5. The solver must be one of the followings: {string_of_solver_keywords}. 
    The turbulence_model must be one of the followings: {string_of_turbulence_model}.
    If a case employs the laminar flow assumption, then the turbulence_model is set to 'null'.
"""

CONVERT_JSON_TO_MD = """Convert the provided JSON string into a Markdown format where:
1. Each top-level JSON key becomes a main heading (#)
2. Its corresponding key-value pairs are rendered as unordered list items
3. Maintain the original key-value hierarchy in list format
The provided json string is as follow:{json_string}.
"""


class ChatBot:
    def __init__(self, system_prompt=SYSTEM_PROMPT, api_key=os.environ.get("DEEPSEEK_R1_KEY"), base_url=os.environ.get("DEEPSEEK_R1_BASE_URL")):
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        self.system_prompt = system_prompt
        self.temperature = 0.9

        self.token_counter = {
            "total": 0,
            "qa_history": []
        }

    def process_document(self, document_file, document_type="application/pdf"):
        if document_type == "application/pdf":
            try:
                pdf_reader = PyPDF2.PdfReader(document_file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text()
                return text
            except Exception as e:
                return f"PDF processing error: {str(e)}"
        elif document_type == "text/plain":
            try:
                text = document_file.read().decode("utf-8", errors="ignore")
                return text
            except Exception as e:
                return f"TXT processing error: {str(e)}"
        else:
            return "Unsupported file type"

    def create_zip_archive(self, source_dir: str, output_filename: str) -> str:
        """Recursively pack everything under source_dir into output_filename.zip."""
        output_path = output_filename + ".zip"
        try:
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for root, dirs, files in os.walk(source_dir):
                    for file in files:
                        full_path = os.path.join(root, file)
                        relative_path = Path(full_path).relative_to(source_dir)

                        # Write the file into the zip using its relative path
                        zf.write(full_path, relative_path)
            return output_path
        except Exception as e:
            return f"Zip creation error: {str(e)}"

    def get_response(self, messages):

        try:
            response = self.client.chat.completions.create(
                model=os.environ.get("DEEPSEEK_R1_MODEL_NAME"),
                messages=[{"role": "system", "content": self.system_prompt}] + messages,
                temperature=self.temperature
            )
            # Record token usage
            usage = response.usage
            self.token_counter["total"] += usage.total_tokens

            return response.choices[0].message.content
        except Exception as e:
            return f"Chat error: {str(e)}"

    def convert_json_to_md(self, json_string: str) -> str:
        """Call the LLM API to convert a JSON string into Markdown format."""
        prompt = CONVERT_JSON_TO_MD.format(json_string=json_string)

        response = self.client.chat.completions.create(
            model=os.environ.get("DEEPSEEK_R1_MODEL_NAME"),
            messages=[{"role": "assistant", "content": prompt}],
            temperature=self.temperature
        )

        return response.choices[0].message.content

    def count_tokens(self, text: str, model: str = "gpt-4o") -> int:
        """Count token numbers using tiktoken"""
        try:
            encoding = tiktoken.encoding_for_model(model)
            return len(encoding.encode(text))
        except KeyError:
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))

def initialize_session_state():
    """ Initialise session state for web interaction logic configuration"""
    # 1. Instantiate the ChatBot
    if "chatbot" not in st.session_state:
        st.session_state.chatbot = ChatBot(
            system_prompt=SYSTEM_PROMPT,
            api_key=os.environ.get("DEEPSEEK_R1_KEY"),
            base_url=os.environ.get("DEEPSEEK_R1_BASE_URL")
        )
    # 2. Initialize Streamlit interaction flags
    if "show_start" not in st.session_state:  # Whether to show the initial hint
        st.session_state.show_start = False
    if "messages" not in st.session_state:    # Chat history
        st.session_state.messages = []
    if "document_processed" not in st.session_state:  # Whether a PDF or TXT file has been uploaded and processed
        st.session_state.document_processed = False
    if "document_content" not in st.session_state:    # Content extracted from the PDF or TXT file
        st.session_state.document_content = None
    if "ask_case_solver" not in st.session_state:     # Whether to prompt the user to choose a case and solver
        st.session_state.ask_case_solver = False
    if "uploaded_mesh" not in st.session_state:       # Whether a mesh file has been uploaded
        st.session_state.uploaded_mesh = False
    if "of_case_zip_generated" not in st.session_state:  # Whether the zip archive has been generated
        st.session_state.of_case_zip_generated = False
    if "wait_for_mesh_to_run" not in st.session_state:   # Once a mesh is uploaded, ChatCFD will start automatically
        st.session_state.wait_for_mesh_to_run = False
    if "run_completed" not in st.session_state:       # Whether the run has completed
        st.session_state.run_completed = False
    if "user_answered" not in st.session_state:
        st.session_state.user_answered = False

def main():
    # 1. Initialize Streamlit
    st.title("ChatCFD: chat to run CFD cases.")
    st.divider()
    initialize_session_state()

    # Display usage hint
    if st.session_state.show_start == False:
        st.header('**Please upload the document to start!**')
        st.session_state.show_start = True

    # 2. Configure the sidebar
    # 2.1 Sidebar: Export chat history
    with st.sidebar:
        st.header("Export chat history")  # export_format = "JSON"
        
        if st.button("Export chat"):
            if not st.session_state.messages:
                st.warning("Empty chat history")
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"chatlog_{timestamp}"

                chat_data = {
                    "metadata": {
                        "export_time": datetime.now().isoformat(),
                        "total_messages": len(st.session_state.messages),
                        "total_tokens": st.session_state.chatbot.token_counter["total"]
                    },
                    "messages": st.session_state.messages
                }
                
                st.sidebar.download_button(
                    label="Download JSON file",
                    data=json.dumps(chat_data, indent=2, ensure_ascii=False),
                    file_name=f"{filename}.json",
                    mime="application/json"
                )

    # 2.2 Sidebar: Document Upload (upload a PDF or TXT describing the case)
    with st.sidebar:
        st.header("Upload Document")
        uploaded_document = st.file_uploader(
            "Please upload a PDF or TXT file",
            type=['pdf', 'txt']
        )

        if uploaded_document:
            if not st.session_state.document_processed:
                document_type = uploaded_document.type
                # Build save path
                path_cfg.document_path = os.path.join(path_cfg.temp_dir, uploaded_document.name.replace(" ", "_"))

                try:
                    # Persist the uploaded PDF or TXT file
                    with open(path_cfg.document_path, "wb") as f:
                        f.write(uploaded_document.getbuffer())

                    case_info.file_name = os.path.basename(path_cfg.document_path).rstrip("txt").rstrip("pdf").rstrip(".")
                    path_cfg.output_path = os.path.join(path_cfg.output_dir, case_info.file_name)

                except Exception as e:
                    st.error(f"Failed at processed the uploaded document: {str(e)}") 

                # Extract content from the PDF or TXT file
                st.session_state.document_content = st.session_state.chatbot.process_document(uploaded_document, document_type)
                if st.session_state.document_content == "Unsupported file type":
                    st.error("Unsupported file type") 

                config.paper_content = st.session_state.document_content
                st.toast("Document uploaded! ", icon="💾")

                # Ask the LLM to extract CFD cases from the document
                question = EXTRACT_CASES_FROM_TEXT_PROMPT.format(document_content=st.session_state.document_content)

                st.session_state.messages.append({
                    "role": "user",
                    "content": question, "timestamp": datetime.now().isoformat()
                })
                
                chatbot_response = st.session_state.chatbot.get_response(st.session_state.messages)
                st.session_state.messages.append({"role": "assistant", "content": chatbot_response, "timestamp": datetime.now().isoformat()})

                # Mark document processing as complete
                st.session_state.document_processed = True

                # Prompt the user to choose a case and solver for simulation
                if not st.session_state.ask_case_solver:
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": ASK_TO_CHOOSE_CASE_AND_SOLVER,
                        "timestamp": datetime.now().isoformat()
                    })
                    st.session_state.ask_case_solver = True

    # 2.3 Sidebar: Mesh Upload
    with st.sidebar:
        st.header("Upload the mesh file")
        uploaded_mesh_file = st.file_uploader(
            "Please upload mesh (only support the Fluent-format .msh)",
            type=['msh']
        )
        if uploaded_mesh_file:
            if not st.session_state.uploaded_mesh:
                # Build save path
                mesh_path = os.path.join(path_cfg.temp_dir, uploaded_mesh_file.name.replace(" ", "_"))

                try:
                    # Persist the uploaded mesh file
                    with open(mesh_path, "wb") as f:
                        f.write(uploaded_mesh_file.getbuffer())
                    st.toast(f"Mesh file saved: {mesh_path}", icon="💾")

                    path_cfg.grid_path = mesh_path

                    # Extract boundary names from the mesh to complete upload
                    grid_info.grid_bc_name = list(file_preparation.extract_boundary_names(mesh_path, config.grid_type))
                    st.toast(f"The mesh file has been processed! ", icon="💾")

                    # Notify the user that the OpenFOAM case is being generated
                    boundary_name = ", ".join(grid_info.grid_bc_name)
                    info_after_mesh_processed = f'''You have uploaded a mesh file with boundary names as: {boundary_name}.\nNow the case are prepared and running in the background. Running information will be shown in the console.'''
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": info_after_mesh_processed,
                        "timestamp": datetime.now().isoformat()
                    })

                    # Update status after processing
                    st.session_state.uploaded_mesh = True

                except Exception as e:
                    st.error(f"Failed to process mesh file: {str(e)}")

    # 2.4 Sidebar: Download OF_case
    with st.sidebar:
        st.header("Download OpenFOAM case")
        # Ensure session-state holders exist
        if "case_zip_bytes" not in st.session_state:
            st.session_state.case_zip_bytes = None
        if "case_zip_filename" not in st.session_state:
            st.session_state.case_zip_filename = None

        # 1) Zip already ready → show download button
        if st.session_state.case_zip_bytes is not None:
            st.download_button(
                label="📥 Download OpenFOAM Case",
                data=st.session_state.case_zip_bytes,
                file_name=st.session_state.case_zip_filename,
                mime="application/zip",
                key='download_case_button'
            )
        # 2) No zip yet → show generation button
        else:
            if st.button("After ChatCFD finishes, click here to show the download button.."):
                if not st.session_state.run_completed:
                    st.warning("OpenFOAM case is still being generated. Please wait.")
                else:
                    try:
                        source_case_dir = path_cfg.output_path
                        temp_zip_filename = os.path.join(path_cfg.temp_dir, os.path.basename(source_case_dir))  # 无需.zip扩展名

                        with st.spinner(f"Zipping case folder: {os.path.basename(source_case_dir)}..."):
                            of_case_zip_path = st.session_state.chatbot.create_zip_archive(
                                source_dir=source_case_dir,
                                output_filename=temp_zip_filename
                            )
                        st.success("OpenFOAM case zipped successfully!")

                        # Prepare download
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")                
                        download_filename = f"{os.path.basename(source_case_dir)}_{timestamp}.zip"
                        
                        with open(of_case_zip_path, "rb") as f:
                            st.session_state.case_zip_bytes = f.read()
                        st.session_state.case_zip_filename = download_filename
                        
                        # Flag success and rerun to switch to download button
                        st.session_state.of_case_zip_generated = True
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error during ZIP creation or download: {e}")

    # 3. Display conversation history
    if len(st.session_state.messages) > 0:
        for message in st.session_state.messages[1:]:
            if message["role"] == "user":
                if message["content"].startswith(EXTRACT_CASES_FROM_TEXT_PROMPT[:100]):  # Skip automatically injected prompts
                    continue
                st.chat_message("user").write(message["content"])
            else:
                if message["content"].startswith("Understand the user's answer") or message["content"].startswith("Convert the provided JSON string into a Markdown format where:"):
                    continue
                elif message["content"].startswith("Based on the user's new request:"):
                    # Extract the actual user request from re-phrasing prompts
                    prompt_extracted = message["content"].split("Based on the user's new request:")[-1].strip()
                    prompt_extracted = prompt_extracted.split("Please modify the existing case configuration according to this request.")[0].strip().rstrip('\"')
                    st.chat_message("assistant").write(prompt_extracted)
                elif message["content"].startswith("Understand the user's answer and describe the case details of the user's requirement."):
                    prompt_extracted = message["content"].split("The user's answer is:")[-1].strip()
                    prompt_extracted = prompt_extracted.split("Please generate JSON content according to these requirements:")[0].strip().rstrip()
                    st.chat_message("assistant").write(prompt_extracted)
                else:
                    try:
                        temp = json.loads(message["content"])  # Do not display JSON-to-Markdown conversions
                        pass
                    except Exception as e:
                        st.chat_message("assistant").write(message["content"])

    # 5. User input
    if prompt := st.chat_input("Enter your requirement or reply."):
        
        st.chat_message("user").write(prompt)  # Display the user's original prompt in the UI

        if st.session_state.ask_case_solver and not st.session_state.wait_for_mesh_to_run: # ask the user for Case_X, solver and turbulence

            guide_case_choose_prompt = CHOOSE_A_CASE_TO_RUN.format(
                user_answer=prompt,
                response_format=JSON_RESPONSE_SAMPLE,
                string_of_solver_keywords=config.string_of_solver_keywords,
                string_of_turbulence_model=config.string_of_turbulence_model
            )

            st.session_state.messages.append({"role": "user", "content": guide_case_choose_prompt, "timestamp": datetime.now().isoformat()})

            # Get assistant's response
            with st.chat_message("assistant"):
                class SimulationRequirement(BaseModel):
                    case_name: str = Field(..., description="The name of the case to be simulated.")
                    solver: str = Field(..., description="The OpenFOAM solver to be used for the simulation.")
                    turbulence_model: str = Field(..., description="The turbulence model to be applied in the simulation.")
                    other_physical_model: str = Field(..., description="Any other physical models to be included in the simulation.")
                    case_specific_description: str = Field(..., description="A detailed description of the specific case setup.")

                qa = QA_NoContext_deepseek_R1()
                response = qa.ask(st.session_state.messages, response_format=PydanticOutputParser(pydantic_object=SimulationRequirement))
                st.session_state.messages.append({"role": "assistant", "content": response, "timestamp": datetime.now().isoformat()})
                # print("response: ", response)

                try:
                    case_info.case_info_simple = json.loads(response)
                    st.session_state.case_info_simple = case_info.case_info_simple

                    st.session_state.messages.append({"role": "user", "content": CONVERT_JSON_TO_MD.format(json_string=response), "timestamp": datetime.now().isoformat()})
                    md_form = st.session_state.chatbot.convert_json_to_md(response).strip("```").lstrip("markdown").strip()
                    st.session_state.md_form = md_form

                    decorated_response = f'''You choose to simulate the cases with the following setups:\n{md_form}'''
                    st.write(decorated_response)
                    st.session_state.messages.append({"role": "assistant", "content": decorated_response, "timestamp": datetime.now().isoformat()})
                    
                    # Move to the “confirm or edit settings” stage; once a mesh is uploaded ChatCFD will start
                    st.session_state.wait_for_mesh_to_run = True
                except json.JSONDecodeError:
                    st.error("Failed to parse the simulation requirements. Please try again.")
                    print(f"JSONDecodeError: Response was: {response}")
                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")
                    print(f"Error: {str(e)}")

        else: 
            # Check whether the user is requesting to modify an existing configuration
            if st.session_state.wait_for_mesh_to_run:
                modification_prompt = (
                    f'Based on the user\'s new request: "{prompt}"\n\n'
                    f'Please modify the existing case configuration according to this request.\n'
                    f'The current configuration is: {json.dumps(case_info.case_info_simple, indent=2)}\n\n'
                    f'Generate an updated content with the same structure but incorporating the requested changes.\n'
                    f'Follow these requirements:\n'
                    f'1. Maintain the same content structure\n'
                    f'2. Ensure strict JSON syntax compliance\n'
                    f'3. Use double quotes for keys and string values\n'
                    f'4. Case_name must only contain [a-zA-Z0-9_]+ \n'
                    f'5. Valid solvers: {config.string_of_solver_keywords}\n'
                    f'6. Valid turbulence models: {config.string_of_turbulence_model}\n\n'
                    'Return the updated complete {response_format} content.'
                )

                st.session_state.messages.append({"role": "user", "content": modification_prompt, "timestamp": datetime.now().isoformat()})
                # Get modified configuration
                with st.chat_message("assistant"):
                    try:
                        # Get structured updates from the user
                        response = qa.ask(st.session_state.messages, response_format=PydanticOutputParser(pydantic_object=SimulationRequirement))

                        # Parse JSON response
                        updated_config = json.loads(response)
                        case_info.case_info_simple = updated_config
                        st.session_state.case_info_simple = updated_config

                        # Convert to Markdown for display
                        st.session_state.messages.append({"role": "user", "content": CONVERT_JSON_TO_MD.format(json_string=response), "timestamp": datetime.now().isoformat()})
                        md_form = st.session_state.chatbot.convert_json_to_md(response)
                        st.session_state.md_form = md_form
                                                
                        # Display confirmation message
                        decorated_response = f'''Based on your request, I've updated the case configuration to:\n{md_form}'''
                        st.write(decorated_response)
                        # Add user-friendly response to chat history
                        st.session_state.messages.append({"role": "assistant", "content": decorated_response, "timestamp": datetime.now().isoformat()})
                    except json.JSONDecodeError:
                        st.write("I couldn't process that as a valid case modification. Please check your request and try again.")
                        st.session_state.messages.append({"role": "assistant", "content": "I couldn't process that as a valid case modification. Please check your request and try again.", "timestamp": datetime.now().isoformat()})
            else:
                # Original normal conversation processing logic
                st.session_state.messages.append({"role": "user", "content": prompt, "timestamp": datetime.now().isoformat()})
                # Get assistant's response
                with st.chat_message("assistant"):
                    response = st.session_state.chatbot.get_response(st.session_state.messages)
                    st.write(response)
                    st.session_state.messages.append({"role": "assistant", "content": response, "timestamp": datetime.now().isoformat()})

    # 6. Based on the user's confirmed simulation case settings, prompt the user to upload the mesh before running ChatCFD
    if st.session_state.document_processed and st.session_state.wait_for_mesh_to_run and not st.session_state.uploaded_mesh:
        # Save the confirmed simulation case settings
        if "md_form" in st.session_state:
            case_info.simulation_requirement = st.session_state.md_form
        elif "md_form" in locals():
            case_info.simulation_requirement = md_form
        else:
            # Fallback if md_form is lost (should not happen if flow is correct)
            case_info.simulation_requirement = ""
            
        st.write("If you don't have further requirement on the case setup. \n**Please upload the mesh of the Fluent .msh format.**")

    # 7. Run ChatCFD after mesh upload
    if st.session_state.uploaded_mesh and st.session_state.document_processed and st.session_state.wait_for_mesh_to_run and not st.session_state.run_completed:
        
        # Restore case_info.case_info_simple to survive Streamlit reruns
        if "case_info_simple" in st.session_state:
            case_info.case_info_simple = st.session_state.case_info_simple

        # Restore document_path to survive reruns
        if "document_path" in st.session_state:
            path_cfg.document_path = st.session_state.document_path

        print(f"case_info.case_info_simple is: {case_info.case_info_simple}")

        # Load pre-processed OpenFOAM tutorials
        print(f"**************** Preprocessing OF tutorials at {config.of_tutorial_dir} ****************")
        preprocess_OF_tutorial.read_in_processed_merged_OF_cases()

        print("case_info.case_info_simple is:", case_info.case_info_simple)
        
        for key, value in case_info.case_info_simple.items():  # key: Case_1, value: {case_name:..., solver:..., turbulence_model:..., case_specific_description:...}
            print(f"***** start processing {key}: {value['case_name']} *****")

            turbulence_model = value.get("turbulence_model", None)
            if turbulence_model not in config.turbulence_model_keywords:
                turbulence_model = None
            other_physical_model = value.get("other_physical_model", None)

            other_model_list = ["GRI", "TDAC", "LTS","common","Maxwell","Stokes"]

            if isinstance(other_physical_model, str):
                other_physical_model = [other_physical_model]
            elif not isinstance(other_physical_model, list):
                other_physical_model = []
            else:
                other_physical_model = []

            other_physical_model = [m for m in other_physical_model if m in other_model_list]
            if not other_physical_model:
                other_physical_model = None

            other_physical_model = value.get("other_physical_model", None)

            # Populate config.info
            case_info.case_name = value["case_name"]
            case_info.case_solver = value["solver"]
            case_info.turbulence_model = turbulence_model
            case_info.other_physical_model = other_physical_model
            case_info.case_description = value["case_specific_description"]

            running_results = main_run_chatcfd.run_case()

            with st.chat_message("assistant"):
                response = st.session_state.chatbot.get_response(st.session_state.messages)
                st.write(f"The running results are:\n{running_results}")
                st.session_state.messages.append({"role": "assistant", "content": response, "timestamp": datetime.now().isoformat()})

            # Prevent re-entry and trigger the zip-download button
            st.session_state.run_completed = True

    # 8. Generate case summary
    if st.session_state.run_completed:
        with st.chat_message("assistant"):


            case_content = get_case_content()
            case_summary = generate_case_summary(case_info.case_description, case_content)

            st.session_state.messages.append({
                "role": "assistant",
                "content": case_summary,
                "timestamp": datetime.now().isoformat()
            })


def main2(txt_file=""):
    # Initialize LLM
    print("==========================ChatCFD==============================")
    client = OpenAI(
            api_key=os.environ.get("DEEPSEEK_R1_KEY"),
            base_url=os.environ.get("DEEPSEEK_R1_BASE_URL")
        )
    
    def basic_chat(messages):
        response= client.chat.completions.create(
            model=os.environ.get("DEEPSEEK_R1_MODEL_NAME"),
            messages=messages,
            temperature=0.9
        )
        return response.choices[0].message.content

    manual_verification = False  # Should manual verification or modification of the configuration for extracting LLM case studies be required?

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # Read txt file content
    with open(txt_file, "r") as f:
        text_content = f.read()

    messages.append({"role": "user","content": EXTRACT_CASES_FROM_TEXT_PROMPT.format(text_content=text_content)})

    cases_in_text = basic_chat(messages)
    messages.append({"role": "assistant", "content": cases_in_text})

    print("\n**Chatbot:**\n", cases_in_text)

    ask_to_choose_case_and_solver = ASK_TO_CHOOSE_CASE_AND_SOLVER

    print("\n**Chatbot:**\n", ask_to_choose_case_and_solver)    

    if manual_verification:
        user_answer = input("Please choose the case you want to simulate and the OpenFOAM solver you want to use: ")
    else:
        # Here you can use a preset answer for testing
        user_answer = "I want to simulate Case_1"

    guide_case_choose_prompt = CHOOSE_A_CASE_TO_RUN.format(
        user_answer=user_answer,
        response_format=JSON_RESPONSE_SAMPLE,
        string_of_solver_keywords=config.string_of_solver_keywords,
        string_of_turbulence_model=config.string_of_turbulence_model
    )

    messages.append({"role": "user", "content": guide_case_choose_prompt})
    get_all_case_dict = False
    max_retries = 3  # Set maximum retry attempts
    retry_count = 0
    while retry_count < max_retries and not get_all_case_dict:
        try:
            case_info.simulation_requirement = basic_chat(messages)

            print(f"**Chatbot:**\n {CONFIRM_SIMULATION_REQUIREMENT.format(simulation_requirement=case_info.simulation_requirement)}")

            case_info_simple = json.loads(case_info.simulation_requirement.lstrip("```json").rstrip("```").strip())
            get_all_case_dict = True
        except json.JSONDecodeError:
            print("Failed to parse JSON response:", case_info.simulation_requirement)
            retry_count += 1
            return

    print(f"**************** Preprocessing OF tutorials at {config.of_tutorial_dir} ****************")

    preprocess_OF_tutorial.read_in_processed_merged_OF_cases()

    for key, value in config.case_info_simple.items():
        case_name = value["case_name"]
        print(f"***** start processing {key}: {case_name} *****")
        solver = value["solver"]

        try:
            turbulence_model = value["turbulence_model"]
        except KeyError:
            value["turbulence_model"] = None
            turbulence_model = None

        if turbulence_model not in config.turbulence_model_keywords:
            value["turbulence_model"] = None
            turbulence_model = None

        case_specific_description = value["case_specific_description"]

        other_physical_model = value["other_physical_model"]

        other_model_list = [
            "GRI", "TDAC", "LTS","common","Maxwell","Stokes"
        ]

        # Unified processing: whether input is string or list, convert to list
        if isinstance(other_physical_model, str):
            other_physical_model = [other_physical_model]
        elif not isinstance(other_physical_model, list):
            other_physical_model = []

        other_physical_model = [m for m in other_physical_model if m in other_model_list]
        if not other_physical_model:
            other_physical_model = None

        # Load information to config.info
        config.case_info.case_name = case_name
        config.case_info.case_solver = solver
        config.case_info.turbulence_model = turbulence_model
        config.case_info.other_physical_model = other_physical_model
        config.case_info.case_description = case_specific_description

        main_run_chatcfd.run_case()


if __name__ == "__main__":

    # ======= **0. You need to make the settings according to the requirements here** =======
    config.run_cfg.run_time = 1
    config.mode = 0    # 0 or 1, corresponding to using streamlit or python for startup
    config.grid_type = "polyMesh"   # msh or polyMesh


    # ======= 1. Program startup settings =======
    if config.mode == 0:  # 0: With frontend, streamlit
        # streamlit run src/chatbot.py --server.port [your port setting, such as 8501]

        config.grid_type = "msh"
        # print("Please use the following command to start the program:")
        # print("  streamlit run src/chatbot.py --server.port [your port setting, such as 8501]")
        # print("Please enter the PDF, mesh file (.msh format), and simulation requirements in the interactive interface...")
    
        main()  # streamlit run src/chatbot.py --server.port 8501

    elif config.mode == 1:  # 1: No frontend, run directly
        # python chatbot.py --document_path <path> --grid_path <path> --run_time <int>
        # such as: python src/chatbot.py --document_path ../dataset_example/Cavity.txt --grid_path ../dataset_example/cavity/polyMesh --run_time 2

        parser = argparse.ArgumentParser(description="ChatCFD: AI-Driven CFD Simulation Setup and Execution")

        parser.add_argument("--document_path", type=str, default=os.path.join(config.path_cfg.root_dir, "pdf/counterFlowFlame2D.txt"), help="Path to the PDF or txt file")  # , required=True
        parser.add_argument("--grid_path", type=str, default=os.path.join(config.path_cfg.root_dir, "grids/combustion_reactingFoam_laminar_counterFlowFlame2D/constant/polyMesh"), help="Path to the grid file (.msh or polyMesh format)")  # , required=True
        parser.add_argument("--run_time", type=int, default=config.run_cfg.run_time, help="number of simulation runs")

        args = parser.parse_args()

        config.path_cfg.document_path = args.document_path
        config.path_cfg.grid_path = args.grid_path
        config.run_cfg.run_time = args.run_time

        if os.path.isfile(config.path_cfg.grid_path) and config.path_cfg.grid_path.endswith(".msh"):
            config.grid_type = "msh"
        elif os.path.isdir(config.path_cfg.grid_path):
            config.grid_type = "polyMesh"
        else:
            sys.exit("Error: grid_path shall be a .msh file or a polyMesh directory")

        print("Your config:")
        print(f"  config.path_cfg.document_path={config.path_cfg.document_path}")
        print(f"  config.path_cfg.grid_path={config.path_cfg.grid_path}")
        print(f"  config.run_cfg.run_time={config.run_cfg.run_time}")

        config.case_info.file_name = os.path.basename(config.path_cfg.document_path).rstrip("txt").rstrip("pdf").rstrip(".")
        config.path_cfg.output_path = os.path.join(config.path_cfg.output_dir, config.case_info.file_name)

        case_stat_path = os.path.join(config.path_cfg.output_dir, "case_stat.txt")
        try:
            main2(config.path_cfg.document_path)

            with open(case_stat_path, "a") as f:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write("="*50 + "\n")
                f.write(f"[{timestamp}] {config.path_cfg.document_path}: success.\n")
            print(f"Success cases: {config.path_cfg.document_path}")
            print(f"Output path: {config.path_cfg.output_path}")
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"\nError processing {config.path_cfg.document_path}: {e}")

            with open(case_stat_path, "a") as f:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write("="*50 + "\n")
                f.write(f"[{timestamp}] {config.path_cfg.document_path}: failure.\n")
                f.write(f"Error details: \n{str(e)}\n")
            print(f"Error cases: {config.path_cfg.document_path}")
    else:
        sys.exit("Error: mode setting shall be 0 or 1")
