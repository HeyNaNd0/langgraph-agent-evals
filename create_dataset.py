
"""Upload the test cases in dataset/ to LangSmith as a dataset."""

import json
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # LangSmith key from .env

from langsmith import Client

DATASET_NAME = "roast-my-yaml"
DATASET_DIR = Path(__file__).parent / "dataset"


def main() -> None:
    client = Client()

    if client.has_dataset(dataset_name=DATASET_NAME):
        print(f"Dataset '{DATASET_NAME}' already exists. Delete it in LangSmith first to re-upload.")
        return

    answer_key = json.loads((DATASET_DIR / "answer_key.json").read_text())

    examples = []
    for filename, expected in answer_key.items():
        examples.append(
            {
                "inputs": {"manifest": (DATASET_DIR / filename).read_text()},
                "outputs": expected,
                "metadata": {"file": filename},
            }
        )

    dataset = client.create_dataset(
        dataset_name=DATASET_NAME,
        description="Kubernetes manifests with planted bugs, plus inputs that should be rejected.",
    )
    client.create_examples(dataset_id=dataset.id, examples=examples)
    print(f"Created dataset '{DATASET_NAME}' with {len(examples)} examples.")


if __name__ == "__main__":
    main()
