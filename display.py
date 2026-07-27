#!/usr/bin/env python3
"""Show the current Pacific time and date on a HD44780 character LCD.

Wiring (Raspberry Pi 3, BCM pin numbering):

    RS  -> GPIO 15
    E   -> GPIO 21
    D4  -> GPIO 20
    D5  -> GPIO 19
    D6  -> GPIO 13
    D7  -> GPIO 6
    LED -> GPIO 16   (backlight; SET THIS to the pin you actually used)

    RW  -> tie to GND (this driver only ever writes)

Note: a Pi GPIO can safely source ~16 mA. If the backlight draws more,
switch it through a transistor/MOSFET rather than straight off the pin.

Displays the time on the top line and the date on the bottom line, then
puts the LCD into its lowest power state. Run on the Pi with:
    python3 display.py
"""

import time
from datetime import datetime
from zoneinfo import ZoneInfo

import RPi.GPIO as GPIO

# --- Pin assignments (BCM numbering) ---------------------------------------
LCD_RS = 15
LCD_E = 21
LCD_D4 = 20
LCD_D5 = 19
LCD_D6 = 13
LCD_D7 = 6
LCD_BACKLIGHT = 16      # <-- CHANGE to the GPIO your backlight is wired to

DATA_PINS = (LCD_D4, LCD_D5, LCD_D6, LCD_D7)

# --- Configuration ----------------------------------------------------------
PACIFIC = ZoneInfo("America/Los_Angeles")   # handles PST/PDT automatically
BACKLIGHT_ACTIVE_HIGH = True                # set False if backlight is on when low

# --- HD44780 constants ------------------------------------------------------
LCD_WIDTH = 16          # characters per line (change to 20 for a 20x4)
LCD_CHR = True          # sending character data
LCD_CMD = False         # sending a command

LINE_1 = 0x80           # DDRAM address of line 1
LINE_2 = 0xC0           # DDRAM address of line 2

# Command bytes
CMD_CLEAR = 0x01
CMD_ENTRY_MODE = 0x06           # cursor moves right, no display shift
CMD_DISPLAY_ON = 0x0C           # display on, cursor off, blink off
CMD_DISPLAY_OFF = 0x08          # display off  (our "sleep")
CMD_FUNCTION_SET = 0x28         # 4-bit, 2 lines, 5x8 font

# Timing (seconds)
E_PULSE = 0.0005
E_DELAY = 0.0005


def lcd_toggle_enable():
    """Pulse the enable line so the LCD latches the current nibble."""
    time.sleep(E_DELAY)
    GPIO.output(LCD_E, True)
    time.sleep(E_PULSE)
    GPIO.output(LCD_E, False)
    time.sleep(E_DELAY)


def lcd_send_byte(bits, mode):
    """Send one byte to the LCD as two 4-bit nibbles (high nibble first)."""
    GPIO.output(LCD_RS, mode)

    # High nibble
    for shift, pin in zip((4, 5, 6, 7), DATA_PINS):
        GPIO.output(pin, bool(bits & (1 << shift)))
    lcd_toggle_enable()

    # Low nibble
    for shift, pin in zip((0, 1, 2, 3), DATA_PINS):
        GPIO.output(pin, bool(bits & (1 << shift)))
    lcd_toggle_enable()


def lcd_backlight(on):
    """Switch the backlight on or off, honoring the configured polarity."""
    GPIO.output(LCD_BACKLIGHT, on if BACKLIGHT_ACTIVE_HIGH else not on)


def lcd_init():
    """Run the HD44780 4-bit initialization sequence."""
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    for pin in (LCD_RS, LCD_E, LCD_BACKLIGHT, *DATA_PINS):
        GPIO.setup(pin, GPIO.OUT)

    lcd_backlight(True)             # backlight on while we show the clock

    time.sleep(0.05)                # wait for LCD power-up
    lcd_send_byte(0x33, LCD_CMD)    # initialize to 8-bit, twice
    lcd_send_byte(0x32, LCD_CMD)    # then switch to 4-bit
    lcd_send_byte(CMD_FUNCTION_SET, LCD_CMD)
    lcd_send_byte(CMD_DISPLAY_ON, LCD_CMD)
    lcd_send_byte(CMD_ENTRY_MODE, LCD_CMD)
    lcd_send_byte(CMD_CLEAR, LCD_CMD)
    time.sleep(0.002)               # clear needs a longer settle


def lcd_string(message, line):
    """Write a centered string to the given line address."""
    message = message.center(LCD_WIDTH)[:LCD_WIDTH]
    lcd_send_byte(line, LCD_CMD)
    for char in message:
        lcd_send_byte(ord(char), LCD_CHR)


def lcd_sleep():
    """Put the LCD into its lowest-power state.

    Clears the screen, issues Display OFF (0x08) so no pixel blocks stay
    lit, and cuts the backlight. The controller keeps its RAM; call
    lcd_init()/lcd_string() again to wake it.
    """
    lcd_send_byte(CMD_CLEAR, LCD_CMD)
    time.sleep(0.002)
    lcd_send_byte(CMD_DISPLAY_OFF, LCD_CMD)
    lcd_backlight(False)


def main():
    lcd_init()

    now = datetime.now(PACIFIC)
    lcd_string(now.strftime("%I:%M:%S %p"), LINE_1)   # e.g. 07:38:42 PM
    lcd_string(now.strftime("%a %b %d %Y"), LINE_2)   # e.g. Sat Jul 26 2026
    time.sleep(5)

    lcd_sleep()
    print("Time and date displayed, LCD now in sleep mode.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    finally:
        # Release the pins; the LCD keeps whatever state it was left in.
        GPIO.cleanup()