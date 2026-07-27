#!/usr/bin/env python3
"""Test script for a HD44780 character LCD wired in 4-bit mode.

Wiring (Raspberry Pi 3, BCM pin numbering):

    RS -> GPIO 15
    E  -> GPIO 21
    D4 -> GPIO 20
    D5 -> GPIO 19
    D6 -> GPIO 13
    D7 -> GPIO 6

    RW -> tie to GND (this driver only ever writes)

Displays two lines of text, waits, then puts the LCD into its lowest
power state (Display OFF). Run on the Pi with: python3 display.py
"""

import time

import RPi.GPIO as GPIO

# --- Pin assignments (BCM numbering) ---------------------------------------
LCD_RS = 15
LCD_E = 21
LCD_D4 = 20
LCD_D5 = 19
LCD_D6 = 13
LCD_D7 = 6

DATA_PINS = (LCD_D4, LCD_D5, LCD_D6, LCD_D7)

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


def lcd_init():
    """Run the HD44780 4-bit initialization sequence."""
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    for pin in (LCD_RS, LCD_E, *DATA_PINS):
        GPIO.setup(pin, GPIO.OUT)

    time.sleep(0.05)                # wait for LCD power-up
    lcd_send_byte(0x33, LCD_CMD)    # initialize to 8-bit, twice
    lcd_send_byte(0x32, LCD_CMD)    # then switch to 4-bit
    lcd_send_byte(CMD_FUNCTION_SET, LCD_CMD)
    lcd_send_byte(CMD_DISPLAY_ON, LCD_CMD)
    lcd_send_byte(CMD_ENTRY_MODE, LCD_CMD)
    lcd_send_byte(CMD_CLEAR, LCD_CMD)
    time.sleep(0.002)               # clear needs a longer settle


def lcd_string(message, line):
    """Write a left-justified string to the given line address."""
    message = message.ljust(LCD_WIDTH)[:LCD_WIDTH]
    lcd_send_byte(line, LCD_CMD)
    for char in message:
        lcd_send_byte(ord(char), LCD_CHR)


def lcd_sleep():
    """Put the LCD into its lowest-power state.

    HD44780 has no true sleep, so we clear the screen and issue Display
    OFF (0x08). The controller keeps its RAM; call lcd_init()/lcd_string()
    again to wake it.
    """
    lcd_send_byte(CMD_CLEAR, LCD_CMD)
    time.sleep(0.002)
    lcd_send_byte(CMD_DISPLAY_OFF, LCD_CMD)


def main():
    lcd_init()

    lcd_string("Hello, Pi!", LINE_1)
    lcd_string("LCD test OK", LINE_2)
    time.sleep(5)

    lcd_sleep()
    print("Text displayed, LCD now in sleep (Display OFF) mode.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    finally:
        # Release the pins; the LCD keeps whatever state it was left in.
        GPIO.cleanup()