#!/bin/bash

cd $HOME

#Clone project
if [ ! -d electrumx-wallet ]; then
  git clone https://github.com/nosferatu500/electrumx-wallet.git
fi

set -e

#Install dependencies for build project
cd electrumx-wallet

sudo apt-get install git pyqt4-dev-tools python-pip python-dev python-slowaes
sudo python3.5 -m pip install pyasn1 pyasn1-modules pbkdf2 tlslite qrcode

pyrcc4 icons.qrc -o gui/qt/icons_rc.py

chmod 775 electrum-xvg

sudo cp -r .electrum-xvg $HOME


./electrum-xvg
