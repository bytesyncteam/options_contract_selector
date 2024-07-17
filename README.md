## Background

This is the Python backend for the monorepo that will generally be running the heavy lifting with financial algorithms

## Installing and Running Theta terminal:
#### install java
```
sudo wget https://download.oracle.com/java/19/latest/jdk-19_linux-x64_bin.deb
sudo apt-get -qqy install ./jdk-19_linux-x64_bin.deb
sudo update-alternatives --install /usr/bin/java java /usr/lib/jvm/jdk-19/bin/java 1919
```
#### install theta terminal
```
sudo mkdir /etc/thetadata
wget https://download-latest.thetadata.us -O /etc/thetadata/ThetaTerminal.jar
```
#### run theta terminal
```
# get username and password from env variables
sudo cd /etc/thetadata
java -jar ThetaTerminal.jar <username> <password>
```
## Run the dev server:

`uvicorn app.main:app --port 8000 --reload`

### Updating tickers
make sure that all the migrations have been run.
to run the script, cd to root directory, activate the virtual env and run the following command:
```bash
python update_tickers.py
```
