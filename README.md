# App Details
Rxminder App is an app that serves as a prescription tracker. It reminds the user when to take a medication and creates notifications automatically for how often you need to take a prescription per day.

## Installation

Backend
in one terminal:
```bash
cd backend
python -m venv .venv
mac: source .venv/bin/activate 
windows: .venv\Scripts\activate
pip install -r requirements.txt
python seed.py
uvicorn main:app --reload --port 8000
```
Frontend
in a separate terminal, run concurretly:
```bash
cd .\rxminder\
npm install
npm expo start
```
this will generate a QR code to scan with the device camera. 
With Expo Go downloaded, it will open the app

## Testing

The two main libraries used for testing in our project are **coverage** and **pytest**. They are included in the requirements.txt file in the /backend directory, and hence should have been installed when you set up the virtual env for running the system.

### Still, let's verify
```bash
pytest --version && coverage --version
```
You'll get the version numbers if everything works well. Otherwise, just manually install the libraries using this command:
```bash
pip install pytest coverage
```
and try verifying again.
### Running the tests
```bash
coverage run -m pytest -q tests.py test_pharmacies.py
```
This will run the tests using pytest and coverage will automatically track statement coverage in the background. For a less verbose output:
```bash
coverage run -m pytest -q --disable-warnings tests.py test_pharmacies.py
```
### Getting statement coverage report
```bash
coverage report
```
Make sure to run this directly after running the tests using the previous command. Expect to see a neat table comprising the coverage of every file in which a statement was executed.
