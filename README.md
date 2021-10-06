# DroneBlocks Python Utils

DroneBlocks Tello drone Python utilities used in many of the advanced Tello programming with Python courses.

Some of the features:

* DroneBlocksTello class that added Robomaster TT commands to the DJITelloPy Tello class
* Aruco marker utilities
* Video image effect utilities
* tello_script_runner to create an easy to use Tello script execution environment


### Install using pip
```shell
pip install https://github.com/dbaldwin/DroneBlocks-Python-Utils/archive/master.zip
```

## Usage

### Simple Tello Example

```python
from droneblocks import DroneBlocksTello

tello = DroneBlocksTello()

tello.connect()
tello.takeoff()

tello.move_up(100)
tello.rotate_counter_clockwise(90)
tello.move_forward(100)

tello.land()

```

### Simple Robomast TT Example
```python
from droneblocks import DroneBlocksTello
import time

tello = DroneBlocksTello()

tello.connect()
tello.clear_display()
tello.takeoff()
tello.display_heart()
tello.move_up(100)
tello.rotate_counter_clockwise(90)
tello.display_smile()
tello.move_forward(100)
time.sleep(2)
tello.clear_display()
tello.land()

```
