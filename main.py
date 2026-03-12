import os
import subprocess
from utilities.clean_files import clean_files

ABAQUS_CMD_PATH = r'C:\SIMULIA\Commands\abq2023.bat'


def main():
    os.environ["BACKEND_PROJECT_PATH"] = os.path.join(os.getcwd(), "backend")
    
    abaqus_command = f'"{ABAQUS_CMD_PATH}" cae startup="backend/command.py"'

    try:
        result = subprocess.run(
            abaqus_command, shell=True, check=True, capture_output=True, text=True
        )
        print("\n=== Abaqus Outputs ===\n")
        print('Retorno:', result.returncode, "\n")
        print('STDOUT:', result.stdout, "\n")
        print('STDERR:', result.stderr)
        print("==========================")
        clean_files()

    except subprocess.CalledProcessError as e:
        print("=== Abaqus 'except' error ===\n")
        print('Retorno:', e.returncode, "\n")
        print('STDOUT:', e.stdout, "\n")
        print('STDERR:', e.stderr)
        print("==========================\n")


if __name__ == "__main__":
    main()

