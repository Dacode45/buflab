#! /bin/bash

./hex2raw < answer1.txt > answer1hex.txt
./bufbomb -u ayekedavidr < answer1hex.txt
