# Control Systems Laboratory Application

This repository provides a comprehensive Python-based visualization application designed for the Control Systems
Laboratory in
the Department of Electrical Engineering Universitas Indonesia. This application facilitates the study and design of
control systems, ranging
from classical root locus and frequency response methods to modern state-space and discrete-time control strategies.

## Overview

The application serves as an interactive educational tool to bridge theoretical concepts with practical simulation. It
allows
users to visualize system dynamics, design controllers (Lead, Lag, PID, Pole-placement), and observe the effects of
sampling in digital control systems.

<hr/>

## Modules Available:

The application is structured into the following analytical modules:

1. Module 2 & 3 Root Locus Techniques and Controller Design
   * Design and validation of Lead, Lag, and Lead-Lag compensators
   * Root locus plotting for LTI systems  
2. Module 4 Frequency Response Techniques
   * Bode plots (Magnitude and Phase)
   * Nyquist stability analysis
3. Module 5 Frequency Response Controller Design
   * Compensator design based on Phase Margin (PM) and Gain Margin (GM) specifications.
4. Module 6 & 7 State Space Modeling, Controller, and Observer Design
   * State space step response simulation 
   * State space state controller (R) and proportional gain (N)
5. Module 8 Discrete Controller and Observer Design
   * Discrete state space step response simulation
   * State controller and Observer of discrete systems
6. Module 9-10 DC Motor Modeling and Controller Design
   * Serial interface with hardware device
   * Real time plotting of physical DC motor variables
   * Closed loop discrete control for DC motor
  
<hr/>

## Instalation

Windows:
```
git clone https://github.com/KevinHutagaol/control-center-2026.git control-center; cd control-center; run.bat
```

Linux: 
```
git clone https://github.com/KevinHutagaol/control-center-2026.git control-center && cd control-center && chmod +x run.sh && ./run.sh
```

<hr/>

**Department of Electrical Engineering** <br/>
Control System Laboratory <br/>
Universitas Indonesia
