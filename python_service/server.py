from uvicorn import run


def main() -> None:
    run("python_service.api:app", host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
