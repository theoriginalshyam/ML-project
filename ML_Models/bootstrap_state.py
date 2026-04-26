from ensemble_inference import RuntimeConfigurationError, bootstrap_state


if __name__ == "__main__":
    try:
        state = bootstrap_state(force=False)
        print(f"Bootstrapped state for {state['current_date']}")
    except RuntimeConfigurationError as exc:
        print(str(exc))
        raise SystemExit(1)
