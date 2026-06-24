# mockforge/engine.py

from faker import Faker
import random
import rstr
from typing import Dict, Any, Iterator
fake = Faker()

DEFAULT_ARRAY_SIZE = (1, 5)

class DataEngine:
    def __init__(self, schema:Dict[str,Any]):
        self.schema = schema

    def _generate_value_by_type(self, data_type: str, constraints: Dict[str, Any]) -> Any:
        """
        Dispatches the generation call based on the data_type string.
        """
        data_type = data_type.lower()
        
        if 'choices' in constraints:
            choices_list = constraints['choices']
            if isinstance(choices_list, list) and choices_list:
                return random.choice(choices_list)

        if data_type == 'string' and 'regex' in constraints:
            regex_pattern = constraints['regex']
            # Use rstr to generate a string that matches the regex pattern
            return rstr.xeger(regex_pattern)

        # --- Primitive Data Types ---
        if data_type == 'string':
            return fake.text(max_nb_chars=constraints.get('max_length', 50))
        elif data_type == 'integer':
            return fake.random_int(min=constraints.get('min', 1), 
                                    max=constraints.get('max', 100))
        elif data_type == 'float':
            return fake.pyfloat(left_digits=constraints.get('precision', 2), 
                                right_digits=constraints.get('scale', 2), 
                                positive=True)
        elif data_type == 'boolean':
            return fake.boolean()
        elif data_type == 'enum':
            choices_list = constraints.get('choices', [])
            if choices_list:
                return random.choice(choices_list)
            return "ERROR: Enum type requires 'choices' list."
        #--- Semantic Data Types ---
        elif data_type == 'uuid':
            return fake.uuid4()
        elif data_type == 'name':
            return fake.name()
        elif data_type in ['username', 'user_name']:
            # Generates a valid fake username (e.g., 'johndoe99')
            return fake.user_name() 
        elif data_type == 'email':
            return fake.email()
        elif data_type == 'phone':
            return fake.phone_number()
        elif data_type == 'date':
            return str(fake.date_this_year()) # Return as string for JSON compatibility
        elif data_type in ['datetime', 'date_time']:
            # IMPORTANT: Return the raw Python datetime object, NOT a string. 
            # This is exactly what SQLAlchemy and SQLite need to bypass that TypeError.
            return fake.date_time()

        # --- File Data Types ---
        elif data_type == 'image_url':
            # Default size 640x480, can be customized
            return fake.image_url(width=constraints.get('width', 640), 
                                height=constraints.get('height', 480))
        elif data_type == 'file_url':
            # Generates a placeholder file URL
            return f"https://example.com/{fake.slug()}.pdf" 

        # --- Complex Data Types (Handling in Phase 1) ---
        elif data_type == 'object':
            # The 'constraints' must contain the nested schema structure
            nested_schema = constraints.get('schema', {})
            # RECURSIVE CALL: Generate a single record using the nested schema
            return self._generate_record(nested_schema)
            
        elif data_type == 'array':
            # The 'constraints' must contain the definition of array elements
            element_def = constraints.get('items', {'type': 'string'}) # Default to string array
            
            min_size, max_size = constraints.get('size', DEFAULT_ARRAY_SIZE)
            array_size = random.randint(min_size, max_size)
            
            generated_array = []
            for _ in range(array_size):
                # RECURSIVE CALL: Generate each element of the array
                # We assume 'element_def' can be a simple string or a full definition dict
                if isinstance(element_def, str):
                    generated_array.append(self._generate_value_by_type(element_def, {}))
                else:
                    generated_array.append(self._generate_value_by_type(element_def['type'], element_def))
                    
            return generated_array
            
        else:
            # Default fallback for unknown types
            return f"UNKNOWN_TYPE_{data_type}"

    
    def _generate_record(self, curr_schema:Dict[str,Any] = None)->Dict[str, Any]:
        record = {}
        if curr_schema is None:
            curr_schema = self.schema
        # Iterate through all field definitions in the schema
        for field_name, definition in curr_schema.items():
            # Handle cases where the type is simple string (MVP format: "field": "name")
            if isinstance(definition, str):
                data_type = definition
                constraints = {}
            # Handle cases where the type is a dictionary (Phase 2 format: "field": {"type": "name", ...})
            elif isinstance(definition, dict) and 'type' in definition:
                data_type = definition['type']
                constraints = definition
            else:
                # Skip invalid schema entries
                print(f"Warning: Invalid schema definition for '{field_name}'. Skipping.")
                continue

            # Use the internal dispatcher to get the generated value
            record[field_name] = self._generate_value_by_type(data_type, constraints)
        return record

    def stream(self, count: int) -> Iterator[Dict[str, Any]]:
        for _ in range(count):
            yield self._generate_record(self.schema)