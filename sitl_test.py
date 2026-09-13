from dronekit import connect, VehicleMode
import time

print("Connecting to simulated drone...")
vehicle = connect('tcp:127.0.0.1:5760', wait_ready=True)

print("Disabling RC failsafe and relaxing arming checks...")
vehicle.parameters['FS_THR_ENABLE'] = 0
vehicle.parameters['ARMING_CHECK'] = 0
time.sleep(3)

print("Waiting for vehicle to become armable...")
while not vehicle.is_armable:
    time.sleep(1)

print("Arming motors...")
vehicle.mode = VehicleMode("GUIDED")
vehicle.armed = True
while not vehicle.armed:
    time.sleep(1)

print("Armed. Mode:", vehicle.mode.name, "Armed:", vehicle.armed)

print("Simulating throttle stick input (RC ch3 = 1500) to unblock old-firmware guided takeoff...")
vehicle.channels.overrides['3'] = 1500
time.sleep(2)

target_altitude = 10
print(f"Taking off to {target_altitude}m...")
vehicle.simple_takeoff(target_altitude)

for _ in range(20):
    alt = vehicle.location.global_relative_frame.alt
    print(f"Altitude: {alt:.1f}m  Mode: {vehicle.mode.name}  Armed: {vehicle.armed}")
    if alt >= target_altitude * 0.95:
        print("Reached target altitude")
        break
    time.sleep(1)

vehicle.channels.overrides = {}
print("Demo complete. Landing...")
vehicle.mode = VehicleMode("LAND")
time.sleep(3)
