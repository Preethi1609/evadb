# coding=utf-8
# Copyright 2018-2023 EvaDB
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os
from time import perf_counter

from gpt4all import GPT4All
import shutil
import subprocess
from typing import Dict
from unidecode import unidecode

import pandas as pd

import evadb

APP_SOURCE_DIR = os.path.abspath(os.path.dirname(__file__))
CURRENT_WORKING_DIR = os.getcwd()  # used to locate evadb_data dir

# default file paths
DEFAULT_CSV_PATH = os.path.join(APP_SOURCE_DIR, "data", "country.csv")

# temporary file paths
QUESTION_PATH = os.path.join(APP_SOURCE_DIR, "question.csv")
SCRIPT_PATH = os.path.join(APP_SOURCE_DIR, "script.py")

def receive_user_input() -> Dict:
    """Receives user input.

    Returns:
        user_input (dict): global configurations
    """
    print(
        "🔮 Welcome to EvaDB! This app lets you to run data analytics on a csv file like in a conversational manner.\nYou will only need to supply a path to csv file and an OpenAI API key.\n\n"
    )
    user_input = dict()

    csv_path = str(
        input("📋 Enter the csv file path (press Enter to use our default csv file): ")
    )

    if csv_path == "":
        csv_path = DEFAULT_CSV_PATH
    user_input["csv_path"] = csv_path

    # get OpenAI key if needed
    # try:
    #     api_key = os.environ["OPENAI_KEY"]
    # except KeyError:
    #     api_key = str(input("🔑 Enter your OpenAI key: "))
    #     os.environ["OPENAI_KEY"] = api_key

    return user_input

def generate_script(cursor: evadb.EvaDBCursor, df: pd.DataFrame, question: str) -> str:
    """Generates script with llm.

    Args:
        cursor (EVADBCursor): evadb api cursor.
        question (str): question to ask to llm.

    Returns
        str: script generated by llm.
    """
    # generate summary
    all_columns = list(df)  # Creates list of all column headers
    df[all_columns] = df[all_columns].astype(str)

    prompt = f"""There is a dataframe in pandas (python). The name of the
            dataframe is df. This is the result of print(df.head()):
            {str(df.head())}. Return a python script with comments to get the answer to the following question: {question}. Do not write code to load the CSV file."""

    llm = GPT4All("ggml-model-gpt4all-falcon-q4_0.bin")

    script_body = llm.generate(prompt)

    return script_body

def run_script(script_body: str, user_input: Dict):
    """Runs script generated by llm.

    Args:
        script_body (str): script generated by llm.
        user_input (Dict): user input.
    """
    absolute_csv_path = os.path.abspath(user_input["csv_path"])
    absolute_script_path = os.path.abspath(SCRIPT_PATH)
    print(absolute_csv_path)
    load_df = f"import pandas as pd\ndf = pd.read_csv('{absolute_csv_path}')\n"
    script_body = load_df + script_body

    with open(absolute_script_path, "w+") as script_file:
        script_file.write(script_body)
    subprocess.run(["python", absolute_script_path])

def cleanup():
    """Removes any temporary file / directory created by EvaDB."""
    if os.path.exists("evadb_data"):
        shutil.rmtree("evadb_data")
    if os.path.exists(QUESTION_PATH):
        os.remove(QUESTION_PATH)
    if os.path.exists(SCRIPT_PATH):
        os.remove(SCRIPT_PATH)


if __name__ == "__main__":
    try:
        # receive input from user
        user_input = receive_user_input()

        # establish evadb api cursor
        print("⏳ Establishing evadb connection...")
        cursor = evadb.connect().cursor()
        print("✅ evadb connection setup complete!")

        # Retrieve Dataframe
        df = pd.read_csv(user_input["csv_path"])

        print("\n===========================================")
        print("🪄 Run anything on the csv table like a conversation!")

        question = str(
            input(
                "What do you want to do with the dataframe? \n(enter 'exit' to exit): "
            )
        )

        if question.lower() != "exit":
            # Generate response with chatgpt udf
            print("⏳ Generating response (may take a while)...")
            script_body = generate_script(cursor, df, question)
            print("+--------------------------------------------------+")
            print("✅ Running this Python script:")
            print(script_body)
            print("+--------------------------------------------------+")

            try:
                run_script(script_body, user_input)
            except Exception as e:
                print(
                    "❗️ Error encountered while running the script. You will likely need to edit the pandas script and run it manually."
                )
                print(e)

        cleanup()
        print("✅ Session ended.")
        print("===========================================")
    except Exception as e:
        cleanup()
        print("❗️ Session ended with an error.")
        print(e)
        print("===========================================")



if __name__ == "__main__":
    main()
