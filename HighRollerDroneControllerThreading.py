import cv2
import pygame
from djitellopy import Tello
import logging
import time
import threading


#Pygame setup for important variables and environment
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
pygame.init()

#Create the display window
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

#Create a black background surface
background = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))

#Create a surface from the logo
logo_surface = pygame.image.load('HighRollerLogo.jpg')
logo_rect = logo_surface.get_rect()
logo_rect.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)

#Initialize the Tello drone
print("Initializing Tello drone...")

drone = Tello()
drone.connect()
#drone.streamon()  #Enable video streaming
print(f"Battery life: {drone.get_battery()}")

#Set logging level for djitellopy to WARNING and above to prevent console clutter
Tello.LOGGER.setLevel(logging.ERROR)

#Game loop variables
clock = pygame.time.Clock()
show_logo = True
show_hud = True
show_controls = False
hasTakenOff = False
velocity_x = 0
velocity_y = 0
velocity_z = 0
rotation_velocity = 0

FPS = 30  #Frame rate for the game loop

class CameraThread:
    def __init__(self, drone):
        self.drone = drone
        self.frame = None
        self.running = False
        self.thread = threading.Thread(target=self.update, daemon=True)

    def start(self):
        self.running = True
        self.drone.streamon()
        self.thread.start()

    def update(self):
        while self.running:
            try:
                frame = self.drone.get_frame_read().frame
                if frame is not None:
                    frame = cv2.flip(frame, 1)  #Flip to match screen orientation
                    self.frame = frame
            except Exception as e:
                print(f"Error in camera thread: {e}")

    def get_frame(self):
        return self.frame

    def stop(self):
        self.running = False
        self.drone.streamoff()
        self.thread.join()
        
class DroneMovementThread:
    def __init__(self, drone):
        self.drone = drone
        self.running = True
        self.velocity_x = 0
        self.velocity_y = 0
        self.velocity_z = 0
        self.rotation_velocity = 0
        self.thread = threading.Thread(target=self.update, daemon=True)
        self.thread.start()

    def update(self):
        """Continuously sends movement commands to the drone without blocking the main loop."""
        while self.running:
            try:
                self.drone.send_rc_control(
                    self.velocity_x, self.velocity_y, self.velocity_z, self.rotation_velocity
                )
                time.sleep(0.05)  # Prevent excessive CPU usage
            except Exception as e:
                print(f"Error in movement thread: {e}")

    def stop(self):
        self.running = False
        self.thread.join()

# Initialize movement thread
movement_thread = DroneMovementThread(drone)


# Initialize camera thread
camera_thread = CameraThread(drone)


#Create a font for text dashboard
font = pygame.font.Font(None, 25)  #Use a default font, or specify your own

#Track key states for rendering
key_states = {
    pygame.K_w: False,
    pygame.K_a: False,
    pygame.K_s: False,
    pygame.K_d: False,
    pygame.K_q: False,
    pygame.K_e: False,
    pygame.K_SPACE: False,
    pygame.K_LCTRL: False,
    pygame.K_l: False,
}
    
#Offsets to make it easier to move controls around
x_offset = 30
y_offset = 440

#Function to render controls
def render_controls():
    box_width = 400
    box_height = 450
    box_x = (SCREEN_WIDTH - box_width) // 2
    box_y = (SCREEN_HEIGHT - box_height) // 2
    box_color = (0, 0, 0, 150)  #Black with 150 alpha (semi-transparent) *Thanks chatGPT for transparency help
    border_color = (255, 255, 255)
    text_color = (255, 255, 255)  #White text

    #Create a surface with per-pixel alpha
    controls_surface = pygame.Surface((box_width, box_height), pygame.SRCALPHA)
    
    #Draw semi-transparent black rectangle
    pygame.draw.rect(controls_surface, box_color, (0, 0, box_width, box_height))
    
    #Draw white border
    pygame.draw.rect(controls_surface, border_color, (0, 0, box_width, box_height), 2) 

    #Control text list
    controls = [
        "W - Move Forward",
        "S - Move Backward",
        "A - Move Left",
        "D - Move Right",
        "Q - Rotate Left",
        "E - Rotate Right",
        "SPACE - Ascend",
        "LCTRL - Descend",
        "L - Land",
        "UP - Flip Forward",
        "DOWN - Flip Backward",
        "LEFT - Flip Left",
        "RIGHT - Flip Right",
        "TAB - Toggle Camera",
        "O - Toggle Controls",
        "H - Toggle HUD"
    ]

    #Render control text on the transparent surface
    line_spacing = 25
    for i, control_text in enumerate(controls):
        text_surface = font.render(control_text, True, text_color)
        text_rect = text_surface.get_rect(center=(box_width // 2, 40 + i * line_spacing))
        controls_surface.blit(text_surface, text_rect)

    #Blit the transparent surface onto the main screen
    screen.blit(controls_surface, (box_x, box_y))

def render_hud():
    # Define colors
    default_color = (255, 255, 255)
    active_color = (0, 255, 0)

    #Key dimensions and spacing
    key_width = 40
    key_height = 40
    
    #Show control tips
    toggle_hud_hint_text = "Toggle Hud - H"
    toggle_hud_hint_surface = font.render(toggle_hud_hint_text, True, (255, 255, 255))
    screen.blit(toggle_hud_hint_surface, (10, 20))
    
    toggle_hud_hint_text = "View Controls - C"
    toggle_hud_hint_surface = font.render(toggle_hud_hint_text, True, (255, 255, 255))
    screen.blit(toggle_hud_hint_surface, (10, 50))

    #Function to draw a key
    def draw_key(x, y, text, is_active, width=key_width):
        color = active_color if is_active else default_color
        pygame.draw.rect(screen, color, (x, y, width, key_height), 2)  #Draw key border
        key_surface = font.render(text, True, color)
        text_rect = key_surface.get_rect(center=(x + width // 2, y + key_height // 2))
        screen.blit(key_surface, text_rect)

    #Draw keys
    draw_key(x_offset + 65, y_offset + 50, "Q", key_states[pygame.K_q])
    draw_key(x_offset + 155, y_offset + 50, "E", key_states[pygame.K_e])
    draw_key(x_offset + 110, y_offset + 90, "W", key_states[pygame.K_w])

    draw_key(x_offset + 65, y_offset + 130, "A", key_states[pygame.K_a])
    draw_key(x_offset + 155, y_offset +  130, "D", key_states[pygame.K_d])

    draw_key(x_offset + 110, y_offset + 170, "S", key_states[pygame.K_s])

    draw_key(x_offset + 160, y_offset + 210, "SPACE", key_states[pygame.K_SPACE], width=100)
    draw_key(x_offset + 0, y_offset + 210, "LCTRL", key_states[pygame.K_LCTRL], width=100)

    # draw_key(x_offset + 200, y_offset + 90, "L", key_states[pygame.K_l])

    try:
        battery_text = f"Battery: {drone.get_battery()}%"
    except Exception:
        battery_text = "Battery: NA"
    battery_surface = font.render(battery_text, True, (255, 255, 255))
    screen.blit(battery_surface, (SCREEN_WIDTH - 200, 50))
    
    try:
        temperature_text = f"Temperature: {int(drone.get_temperature())}°F"
    except Exception:
        temperature_text = "Temperature: NA"
    temperature_surface = font.render(temperature_text, True, (255, 255, 255))
    screen.blit(temperature_surface, (SCREEN_WIDTH - 200, 80))
    
    try:
        height_text = f"Height: {int(drone.get_height())}cm"
    except Exception:
        height_text = "Height: NA"
    height_surface = font.render(height_text, True, (255, 255, 255))
    screen.blit(height_surface, (SCREEN_WIDTH - 200, 110))
    
    try:
        barometer_text = f"Barometer: {int(drone.get_barometer())}cm"
    except Exception:
        barometer_text = "Barometer: NA"
    barometer_surface = font.render(barometer_text, True, (255, 255, 255))
    screen.blit(barometer_surface, (SCREEN_WIDTH - 200, 140))
     
    
    last_flight_time = 0  #Stores the last valid flight time
    try:
        current_flight_time = int(drone.get_flight_time())
        last_flight_time = current_flight_time
    except Exception:
        current_flight_time = last_flight_time  #Display last known flight time if unable to get flight time from drone
    
    flight_time_text = f"Flight Time: {current_flight_time}s"
    flight_time_surface = font.render(flight_time_text, True, (255, 255, 255))
    screen.blit(flight_time_surface, (SCREEN_WIDTH - 200, 170))


################################################################################

#Run the game loop

running = True
try:
    while running:
    
        for event in pygame.event.get():
            #User clicked the X to close the program
            if event.type == pygame.QUIT:
                if hasTakenOff == True:
                    drone.land()
                running = False
    
            if event.type == pygame.KEYDOWN:
                #Toggle between logo and drone feed with tab
                if event.key == pygame.K_TAB:
                    show_logo = not show_logo
                
                    if show_logo:  
                        print("Turning Camera Off...")
                        camera_thread.stop()  # ✅ Proper way to stop the camera thread
                    else:
                        print("Turning Camera On...")
                        camera_thread.start()  # ✅ Proper way to start the camera thread

                                
                #Toggle hud.
                if event.key == pygame.K_h:
                    show_hud = not show_hud
                    
                #Toggle controls.
                if event.key == pygame.K_c:
                    show_controls = not show_controls
                

                        
                #Takeoff on space
                if event.key == pygame.K_SPACE and hasTakenOff == False:
                    try:
                        drone.takeoff()
                        hasTakenOff = True
                        print("Taking Off...")
                    except Exception as e:
                        print(f"Error during takeoff: {e}")
                        
                #Land on l
                if event.key == pygame.K_l and hasTakenOff == True:
                    hasTakenOff = False
                    drone.land()
                
                #Flip forward
                if event.key == pygame.K_UP and hasTakenOff == True:
                    if drone.get_battery() < 50:
                        print("Battery too low to perform a flip.")
                    else:
                        drone.flip_forward()
                #Flip backward
                if event.key == pygame.K_DOWN and hasTakenOff == True:
                    if drone.get_battery() < 50:
                        print("Battery too low to perform a flip.")
                    else:
                        drone.flip_back()
                #Flip left
                if event.key == pygame.K_LEFT and hasTakenOff == True:
                    if drone.get_battery() < 50:
                        print("Battery too low to perform a flip.")
                    else:
                        drone.flip_left()
                #Flip right
                if event.key == pygame.K_RIGHT and hasTakenOff == True:
                    if drone.get_battery() < 50:
                        print("Battery too low to perform a flip.")
                    else:
                        drone.flip_right()
                    
                
            
    #End of Events
    ################################################################################
    #Check for key holds
        keys = pygame.key.get_pressed()
        #
        #Forward / Backward
        if keys[pygame.K_w] and keys[pygame.K_s]:
            key_states[pygame.K_w] = True
            key_states[pygame.K_s] = True
            velocity_y = 0
        elif keys[pygame.K_w]:
            key_states[pygame.K_w] = True
            velocity_y = 100
        elif keys[pygame.K_s]:
            key_states[pygame.K_s] = True
            velocity_y = -100
        else:
            velocity_y = 0
            key_states[pygame.K_w] = False
            key_states[pygame.K_s] = False
            
        #Left / Right
        if keys[pygame.K_a] and keys[pygame.K_d]:
            key_states[pygame.K_a] = True
            key_states[pygame.K_d] = True
            velocity_x = 0
        elif keys[pygame.K_d]:
            key_states[pygame.K_d] = True
            velocity_x = 100
        elif keys[pygame.K_a]:
            key_states[pygame.K_a] = True
            velocity_x = -100
        else:
            velocity_x = 0
            key_states[pygame.K_a] = False
            key_states[pygame.K_d] = False
            
        #Up / Down
        if keys[pygame.K_SPACE] and keys[pygame.K_LCTRL]:
            key_states[pygame.K_SPACE] = True
            key_states[pygame.K_LCTRL] = True
            velocity_z = 0
        elif keys[pygame.K_SPACE]:
            key_states[pygame.K_SPACE] = True
            velocity_z = 100
        elif keys[pygame.K_LCTRL]:
            key_states[pygame.K_LCTRL] = True
            velocity_z = -100
        else:
            key_states[pygame.K_SPACE] = False
            key_states[pygame.K_LCTRL] = False
            velocity_z = 0
            
        #Rotation
        if keys[pygame.K_q] and keys[pygame.K_e]:
            key_states[pygame.K_q] = True
            key_states[pygame.K_e] = True
            rotation_velocity = 0
        elif keys[pygame.K_q]:
            key_states[pygame.K_q] = True
            rotation_velocity = -100
        elif keys[pygame.K_e]:
            key_states[pygame.K_e] = True
            rotation_velocity = 100
        else:
            key_states[pygame.K_q] = False
            key_states[pygame.K_e] = False
            rotation_velocity = 0
        
        # Update movement thread values instead of sending commands directly
        movement_thread.velocity_x = 100 if keys[pygame.K_d] else -100 if keys[pygame.K_a] else 0
        movement_thread.velocity_y = 100 if keys[pygame.K_w] else -100 if keys[pygame.K_s] else 0
        movement_thread.velocity_z = 100 if keys[pygame.K_SPACE] else -100 if keys[pygame.K_LCTRL] else 0
        movement_thread.rotation_velocity = 100 if keys[pygame.K_e] else -100 if keys[pygame.K_q] else 0

                
    ###############################################################################
    
        #Display either the logo or the drone's video feed
        if show_logo:
            screen.blit(logo_surface, logo_rect)
        else:
            frame = camera_thread.get_frame()
            if frame is not None:
                #Create a Pygame surface from the frame
                drone_surface = pygame.surfarray.make_surface(frame)
        
                #Rotate and scale the drone surface to fit the screen minus the dashboard
                drone_surface = pygame.transform.rotate(drone_surface, -90)
                drone_surface = pygame.transform.scale(drone_surface, (SCREEN_WIDTH, SCREEN_HEIGHT))
                screen.blit(drone_surface, (0, 0))
            
        #Show Hud if toggled
        if show_hud:
            render_hud()
            
        #Show controls
        if show_controls:
            render_controls()
            
    ###############################################################################
         
        pygame.display.update()
    
        #Limit the frame rate
        clock.tick(FPS)
    
    #End of game loop
    ###############################################################################
    
    

except KeyboardInterrupt:
    print("Force Quiting Program due to interupt...")
    
finally:
    #Shut down the Tello and Pygame
    drone.send_rc_control(0, 0, 0, 0)
    camera_thread.stop()  # ✅ This safely stops the camera thread and the drone stream
    movement_thread.stop()  # ✅ Stop movement thread
    camera_thread.stop()  # ✅ Stop camera thread
    drone.send_rc_control(0, 0, 0, 0)  # ✅ Make sure the drone stops moving
    drone.end()
    print("Terminating drone connection...")
    pygame.quit()
    print("Quiting PyGame...")
