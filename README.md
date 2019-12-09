# SCILLA

SCILLA is a software for automated discovery of superconducting circuits.
Its goal is to facilitate hardware design for quantum information processing applications.
Starting from a desired target property for the circuit, it provides a closed-loop implementation of circuit design, property computation, and merit evaluation that searches the design space and identifies promising circuits.
The software and its scientific application are described in ref [1].
Implementation details and examples are provided in the supplementary information of the manuscript.

The script `main_benchmark.py` is provided as an example and benchmark of SCILLA.
It searches the space of 2-node superconducting circuits for a flux spectrum that matches the capacitatively shunted flux qubit.
The script is executed with the following command:
```python
python main_benchmark.py
```


### Requirements

This code has been tested with Python 3.6 on Unix platforms.
The required packages are listed in the `environment.yml` file.


### Disclaimer

Note: This repository is under construction. We hope to add further details on the method, instructions and more examples in the near future. 


### Experiencing problems? 

Please create a [new issue](https://github.com/aspuru-guzik-group/SCILLA/issues/new) and describe your problem in detail so we can fix it.


### Authors

This software is written by [Tim Menke](https://github.com/Timmenke) and [Florian Häse](https://github.com/FlorianHase).


### References

[1] Tim Menke, Florian Häse, Simon Gustavsson, Andrew J. Kerman, William D. Oliver, and Alán Aspuru-Guzik, [Automated discovery of superconducting circuits and its application to 4-local coupler design](https://arxiv.org/abs/1912.xxxxx), arXiv preprint arXiv:1912.xxxxx (2019).
