# App Details
Rxminder App is an app that serves as a prescription tracker. It reminds the user when to take a medication and creates notifications automatically for how often you need to take a prescription per day.

## Installation

Use the package manager  to install ______.

```bash
pip install 
```

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
This will run the tests using pytest and coverage will automatically track statement coverage in the background.

### Getting statement coverage report
```bash
coverage report
```
Make sure to run this directly after running the tests using the previous command. Expect to see a neat table comprising the coverage of every file in which a statement was executed.
