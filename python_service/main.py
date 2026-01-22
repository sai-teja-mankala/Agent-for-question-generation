import json
import sys

from agent import run_pipeline


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(
            "Usage: python main.py '<json-payload>' or python main.py path/to/payload.json"
        )

    input_arg = sys.argv[1]
    try:
        if input_arg.endswith(".json"):
            with open(input_arg, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        else:
            payload = json.loads(input_arg)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON input: {exc}") from exc

    result = run_pipeline(payload)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
