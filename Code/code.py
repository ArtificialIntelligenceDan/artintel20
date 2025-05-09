import time
import board
import digitalio
import rotaryio
import usb_hid
import displayio
import terminalio

from adafruit_displayio_ssd1306 import SSD1306
from adafruit_display_text import label

from adafruit_matrixkeypad import Matrix_Keypad
from adafruit_debouncer import Debouncer

from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
from adafruit_hid.consumer_control import ConsumerControl
from adafruit_hid.consumer_control_code import ConsumerControlCode
from adafruit_hid.mouse import Mouse

displayio.release_displays()

# --- OLED Display Setup ---
i2c = board.I2C()
display_bus = displayio.I2CDisplay(i2c, device_address=0x3C)
WIDTH = 128
HEIGHT = 32
display = SSD1306(display_bus, width=WIDTH, height=HEIGHT)
splash = displayio.Group()
display.root_group = splash

# Status text (left side only)
status_text = label.Label(terminalio.FONT, text="KB2040 ready", color=0xFFFFFF, x=0, y=10)
splash.append(status_text)

def show_status(message):
    status_text.text = message

# --- HID Setup ---
keyboard = Keyboard(usb_hid.devices)
cc = ConsumerControl(usb_hid.devices)
mouse = Mouse(usb_hid.devices)

# --- Key Matrix ---
cols = [board.D0, board.D1, board.D2, board.D3]
rows = [board.D4, board.D5, board.D6, board.D7, board.D8]

col_pins = [digitalio.DigitalInOut(pin) for pin in cols]
row_pins = [digitalio.DigitalInOut(pin) for pin in rows]

for pin in col_pins + row_pins:
    pin.direction = digitalio.Direction.INPUT
    pin.pull = digitalio.Pull.DOWN

keys = [
    ["NumLock", "/", "*", "-"],
    ["7", "8", "9", "+"],
    ["4", "5", "6", "^"],
    ["1", "2", "3", "("],
    ["0", ".", ")", "="],
]

keypad = Matrix_Keypad(row_pins, col_pins, keys)

char_map = {
    "0": Keycode.ZERO,
    "1": Keycode.ONE,
    "2": Keycode.TWO,
    "3": Keycode.THREE,
    "4": Keycode.FOUR,
    "5": Keycode.FIVE,
    "6": Keycode.SIX,
    "7": Keycode.SEVEN,
    "8": Keycode.EIGHT,
    "9": Keycode.NINE,
    "/": Keycode.FORWARD_SLASH,
    "*": Keycode.KEYPAD_ASTERISK,
    "-": Keycode.MINUS,
    "+": Keycode.KEYPAD_PLUS,
    ".": Keycode.PERIOD,
    "=": Keycode.EQUALS,
}

previous_keys = set()
numlock_enabled = False

# --- Encoders ---
encoder1 = rotaryio.IncrementalEncoder(board.A1, board.A0)
encoder2 = rotaryio.IncrementalEncoder(board.A2, board.A3)
last_position1 = encoder1.position
last_position2 = encoder2.position

enc1_button_pin = digitalio.DigitalInOut(board.D9)
enc1_button_pin.direction = digitalio.Direction.INPUT
enc1_button_pin.pull = digitalio.Pull.UP
enc1_button = Debouncer(enc1_button_pin)

enc2_button_pin = digitalio.DigitalInOut(board.D10)
enc2_button_pin.direction = digitalio.Direction.INPUT
enc2_button_pin.pull = digitalio.Pull.UP
enc2_button = Debouncer(enc2_button_pin)

print("KB2040 macro pad ready")

while True:
    current_keys = set(keypad.pressed_keys)
    new_keys = current_keys - previous_keys

    for key in new_keys:
        if key == "NumLock":
            numlock_enabled = not numlock_enabled
            show_status(f"NumLock: {'ON' if numlock_enabled else 'OFF'}")

        elif key == "(":
            keyboard.press(Keycode.LEFT_SHIFT, Keycode.NINE)
            keyboard.release_all()
            show_status("Sent (")

        elif key == ")":
            keyboard.press(Keycode.LEFT_SHIFT, Keycode.ZERO)
            keyboard.release_all()
            show_status("Sent )")

        elif key == "^":
            keyboard.press(Keycode.LEFT_SHIFT, Keycode.SIX)
            keyboard.release_all()
            show_status("Sent ^")

        else:
            code = char_map.get(key)
            if code:
                keyboard.press(code)
                keyboard.release_all()
                show_status(f"Sent key: {key}")

    previous_keys = current_keys

    # --- Encoder 1: Volume ---
    current_position1 = encoder1.position
    if current_position1 != last_position1:
        delta = current_position1 - last_position1
        if delta > 0:
            cc.send(ConsumerControlCode.VOLUME_INCREMENT)
            show_status("Volume up")
        else:
            cc.send(ConsumerControlCode.VOLUME_DECREMENT)
            show_status("Volume down")
        last_position1 = current_position1

    # --- Encoder 2: Media Control ---
    current_position2 = encoder2.position
    if current_position2 != last_position2:
        delta = current_position2 - last_position2
        if delta < 0:
            cc.send(ConsumerControlCode.SCAN_NEXT_TRACK)
            show_status("Next track")
        else:
            cc.send(ConsumerControlCode.SCAN_PREVIOUS_TRACK)
            show_status("Previous track")
        last_position2 = current_position2

    # --- Buttons ---
    enc1_button.update()
    enc2_button.update()

    if enc1_button.fell:
        cc.send(ConsumerControlCode.MUTE)
        show_status("Mute toggled")

    if enc2_button.fell:
        cc.send(ConsumerControlCode.PLAY_PAUSE)
        show_status("Play/Pause toggled")

    time.sleep(0.01)
