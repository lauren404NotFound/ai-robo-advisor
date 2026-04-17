"""
Robo-advisory demo selector for Deep Atomic IQ.

Usage:
    - Answer the six survey questions when prompted.
    - The script will select a profile, map it to a Robo folder,
      load performance.csv from that folder, and display it.
"""

import os
import sys

import pandas as pd


def parse_level(answer: str) -> int:
    """
    Map user input to level 0 (Low), 1 (Moderate), 2 (High).

    Accepts:
        - '1', 'low', 'l', 'short'
        - '2', 'medium', 'moderate', 'm'
        - '3', 'high', 'h', 'long'
    """
    a = answer.strip().lower()

    if a in {"1", "l", "low", "short"}:
        return 0
    if a in {"2", "m", "med", "medium", "moderate"}:
        return 1
    if a in {"3", "h", "high", "long"}:
        return 2

    raise ValueError(f"Unrecognised level: {answer!r}. Please use 1/2/3 or Low/Moderate/High.")


def ask_level(question_text: str) -> int:
    """
    Repeatedly prompt for a valid level until the user provides one.
    """
    while True:
        try:
            ans = input(question_text + " [1=Low, 2=Moderate, 3=High]: ")
            level = parse_level(ans)
            return level
        except ValueError as e:
            print(e)
            print("Please try again.\n")


def choose_profile(R: int, H: int, D: int, E: int, S: int, T: int) -> str:
    """
    Implement the six-profile mapping logic.

    R: Risk tolerance / volatility comfort            (0=Low, 1=Moderate, 2=High)
    H: Investment horizon                            (0=Short, 1=Medium, 2=Long)
    D: Diversification preference                    (0=Low, 1=Moderate, 2=High)
    E: Ethical / ESG investment priority             (0=Low, 1=Moderate, 2=High)
    S: Sector / industry exposure preference         (0=Low, 1=Moderate, 2=High)
    T: Portfolio turnover preference                 (0=Low, 1=Moderate, 2=High)

    Returns: "P1", "P2", ..., "P6"
    """
    risk_index = 0.5 * (R + H)

    # 1. ESG–driven, broad and stable -> P4
    if E == 2 and D >= 1:
        return "P4"

    # 2. Very cautious, low turnover -> P1
    if risk_index <= 0.5 and T == 0:
        return "P1"

    # 3. Highly aggressive, high turnover, sector views -> P3
    if risk_index >= 1.5 and T == 2 and S >= 1:
        return "P3"

    # 4. Systematic risk-parity style -> P6
    if D == 2 and S == 0:
        return "P6"

    # 5. Thematic / concentrated -> P5
    if S == 2 and D <= 1:
        return "P5"

    # 6. Fallback balanced profile -> P2
    return "P2"


PROFILE_TO_FOLDER = {
    "P1": "Robo1",
    "P2": "Robo2",
    "P3": "Robo3",
    "P4": "Robo4",
    "P5": "Robo5",
    "P6": "Robo6",
}


def display_dataframe(df: pd.DataFrame) -> None:
    """
    Display the DataFrame nicely in a Jupyter notebook if possible,
    otherwise print a plain-text table to stdout.
    """
    try:
        # If running inside IPython / Jupyter, this will succeed
        from IPython.display import display  # type: ignore

        display(df)
    except Exception:
        # Fallback to plain text
        print(df.to_string())


def main() -> None:
    print("=== Deep Atomic IQ – Robo-Advisory Demo ===\n")
    print("Please answer each question with 1/2/3 or Low/Moderate/High.")
    print("")

    # Survey questions (levels 0,1,2)
    R = ask_level("1. Risk tolerance / volatility comfort")
    H = ask_level("2. Investment horizon")
    D = ask_level("3. Diversification preference")
    E = ask_level("4. Ethical / ESG investment priority")
    S = ask_level("5. Sector / industry exposure preference")
    T = ask_level("6. Portfolio turnover preference")

    profile = choose_profile(R, H, D, E, S, T)
    folder = PROFILE_TO_FOLDER.get(profile)

    if folder is None:
        print(f"Internal error: No folder mapping defined for profile {profile}.")
        sys.exit(1)

    performance_path = os.path.join(folder, "performance.csv")

    if not os.path.exists(performance_path):
        print(f"Could not find performance.csv for profile {profile}.")
        print(f"Expected path: {performance_path}")
        sys.exit(1)

    print("\n--------------------------------------------------")
    print(f"Selected profile: {profile}  ->  folder: {folder}")
    print(f"Loading: {performance_path}")
    print("--------------------------------------------------\n")

    # Adjust index_col as needed depending on your CSV structure
    try:
        df = pd.read_csv(performance_path, index_col=0)
    except Exception as e:
        print(f"Error reading {performance_path}: {e}")
        sys.exit(1)

    display_dataframe(df)


if __name__ == "__main__":
    main()
