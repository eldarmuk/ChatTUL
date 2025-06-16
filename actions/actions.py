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
from rasa_sdk.types import DomainDict

# Load the data source once
with open("datasources.json", encoding="utf-8") as f:
    DATA = json.load(f)

class ActionFieldInfo(Action):
    def name(self) -> Text:
        return "action_field_info"

    async def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict) -> List[Dict[Text, Any]]:
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


class ActionUtterDeadline(Action):
    def name(self) -> Text:
        return "action_utter_deadline"
    
    async def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict) -> List[Dict[Text, Any]]:
        
        # TODO: this need to be finished

        admission_semester = tracker.get_slot("admission_semester")
        study_cycle = tracker.get_slot("study_cycle")
        admission_round = next(tracker.get_latest_entity_values("admission_round"), None)
        process_type = next(tracker.get_latest_entity_values("process_type"), None)

        if not process_type:
            dispatcher.utter_message(
                text="Sorry but I have a problem understanding which admission process you are referring to. Could you clarify?")
            return []
        
        if admission_semester and admission_semester == "summer":
            dispatcher.utter_message(
                text=("Since you mentioned summer semester, "
                    + "I am going to assume you also mean Masters study cycle "
                    + "since it's the only one having admissions during that time")
            )
            study_cycle = "masters"
        
        first_round = not admission_round or admission_round == "first round"
        second_round = not admission_round or admission_round == "second round"

        

        dispatcher.utter_message(
            text="You should check [deadlines page](https://apply.p.lodz.pl/en/enrollment/enroll/deadlines) for precise dates"
        )
        return []