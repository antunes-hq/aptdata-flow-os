#!/usr/bin/env python
import sys
import os

# Add the root directory to sys.path to resolve 'domain' correctly
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from aptdata.core.yaml_builder import YamlSystemBuilder
from aptdata.core.registry import ComponentRegistry

def main():
    print("Building system from YAML...")
    yaml_path = os.path.join(current_dir, "pipeline.yaml")
    builder = YamlSystemBuilder(yaml_path)
    system = builder.build()

    print(f"Running system: {system.system_id}")
    system.run()
    print("Execution finished successfully!")

if __name__ == "__main__":
    main()
