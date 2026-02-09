# data_loader.py - Data loading utilities

import json
import logging

logger = logging.getLogger(__name__)


def load_data():
    """Load data from JSON file
    
    Supports two formats:
    1. Legacy format: Top-level keys with 'Revision'
    2. New format: Nested 'DATA' key with 'CURRENT_REVISION'
    
    Returns:
        tuple: (data_dict, revision) on success
    
    Raises:
        FileNotFoundError: If data.json doesn't exist
        ValueError: If data.json is invalid
    """
    try:
        with open('data.json', 'r') as f:
            raw_data = json.load(f)
            
            # Check if this is new format (nested DATA key)
            if 'DATA' in raw_data:
                data_content = raw_data['DATA']
                revision = raw_data.get('CURRENT_REVISION', 0)
            else:
                # Legacy format - all keys at top level
                # Extract only the data keys, not metadata
                data_keys = ['sid_to_sloc', 'sid_to_sname', 'train_names', 'offday', 'tid_to_stations']
                data_content = {k: raw_data[k] for k in data_keys if k in raw_data}
                revision = raw_data.get('CURRENT_REVISION', raw_data.get('Revision', 0))
            
            logger.info(f"Loaded data.json successfully (revision: {revision})")
            logger.info(f"  - {len(data_content.get('train_names', {}))} trains")
            logger.info(f"  - {len(data_content.get('sid_to_sname', {}))} stations")
            return data_content, revision
    except FileNotFoundError:
        logger.error("data.json not found")
        raise FileNotFoundError("data.json is required but not found")
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in data.json: {e}")
        raise ValueError(f"data.json contains invalid JSON: {e}")
