# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions


# This is a simple example for a custom action which utters "Hello World!"

# from typing import Any, Text, Dict, List
#
# from rasa_sdk import Action, Tracker
# from rasa_sdk.executor import CollectingDispatcher
#
#
# class ActionHelloWorld(Action):
#
#     def name(self) -> Text:
#         return "action_hello_world"
#
#     def run(self, dispatcher: CollectingDispatcher,
#             tracker: Tracker,
#             domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
#
#         dispatcher.utter_message(text="Hello World!")
#
#         return []

import json
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet

# Load the data source once
with open("datasources.json", encoding="utf-8") as f:
    DATA = json.load(f)

class ActionFieldInfo(Action):
    def name(self) -> Text:
        return "action_field_info"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        field = tracker.get_slot("field_of_study")
        if field and field in DATA["field_of_study"]:
            info = DATA["field_of_study"][field]
            text = f"{field} ({info['cycle']}, {info['mode']}, in {info['language']}) at TUL:\n"
            text += f"- Duration: {info['duration_semesters']} semesters ({info['duration_years']} years)\n"
            text += f"- Title: {info['title']}\n"
            text += f"- Highlights: {', '.join(info['curriculum_highlights'])}\n"
            text += f"More details: {info['url']}"
            dispatcher.utter_message(text=text)
        else:
            dispatcher.utter_message(text="Please specify a valid field of study (e.g., Computer Science).")
        return []
