from typing import Dict, Text, Any, List
from rasa.engine.graph import GraphComponent, ExecutionContext
from rasa.engine.recipes.default_recipe import DefaultV1Recipe
from rasa.engine.storage.resource import Resource
from rasa.engine.storage.storage import ModelStorage
from rasa.shared.nlu.training_data.message import Message
from rasa.shared.nlu.training_data.training_data import TrainingData
import re

@DefaultV1Recipe.register(
    DefaultV1Recipe.ComponentType.MESSAGE_FEATURIZER, is_trainable=False
)
class TextNormalizer(GraphComponent):
    
    SPECIAL_TERMS = [
        "IFE",
        "TUL",
        "CS",
        "Computer Science",
        "Business Studies",
        "Architecture",
        "Information Technology",
        "Modelling and Data Science",
        "Digital Management",
        "Advanced Biobased and Bioinspired Materials",
        "Biomedical Engineering and Technologies",
        "Business, Society and Technology",
        "Electronic and Telecommunication Engineering",
        "Industrial Biotechnology",
        "Mathematical Methods in Data Analysis",
        "Mechanical Engineering",
        "Textiles and Fashion Industry"
    ]
    
    @classmethod
    def create(
        cls,
        config: Dict[Text, Any],
        model_storage: ModelStorage,
        resource: Resource,
        execution_context: ExecutionContext,
    ) -> "TextNormalizer":
        return cls()

    def process_training_data(self, training_data: TrainingData) -> TrainingData:
        for example in training_data.training_examples:
            self._normalize_message(example)
        return training_data

    def process(self, messages: List[Message]) -> List[Message]:
        for message in messages:
            self._normalize_message(message)
        return messages

    def _normalize_message(self, message: Message) -> None:
        if message.get("text"):
            original_text = message.get("text")
            normalized_text = self._preserve_special_terms_and_lowercase(original_text)
            message.set("text", normalized_text)
    
    def _preserve_special_terms_and_lowercase(self, text: str) -> str:
        placeholders = {}
        modified_text = text
        
        sorted_terms = sorted(self.SPECIAL_TERMS, key=len, reverse=True)
        
        for i, term in enumerate(sorted_terms):
            placeholder = f"__SPECIAL_TERM_{i}__"
            pattern = re.compile(re.escape(term), re.IGNORECASE)
            if pattern.search(modified_text):
                placeholders[placeholder] = term
                modified_text = pattern.sub(placeholder, modified_text)
        
        modified_text = modified_text.lower()
        
        for placeholder, original_term in placeholders.items():
            modified_text = modified_text.replace(placeholder, original_term)
        
        return modified_text