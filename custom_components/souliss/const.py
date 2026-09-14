"""Constants for the Souliss integration."""

DOMAIN = "souliss"

CONF_GATEWAY_PORT = "gateway_port"
CONF_LOCAL_PORT = "local_port"
CONF_USER_INDEX = "user_index"
CONF_NODE_INDEX = "node_index"

DEFAULT_GATEWAY_PORT = 230
DEFAULT_LOCAL_PORT = 23000
DEFAULT_USER_INDEX = 71
DEFAULT_NODE_INDEX = 121

PING_INTERVAL = 30
SUBSCRIPTION_INTERVAL = 30
# Subscriptions only deliver data on change; poll to keep idle nodes fresh.
POLL_INTERVAL = 60
HEALTH_INTERVAL = 60
REDISCOVERY_INTERVAL = 300
OFFLINE_TIMEOUT = 95
DEFAULT_SLEEP_CYCLES = 5

PLATFORMS = [
    "alarm_control_panel",
    "binary_sensor",
    "button",
    "climate",
    "cover",
    "light",
    "number",
    "sensor",
    "switch",
]

# MaCaco / Souliss UDP functional codes
FUNC_FORCE = 0x33
FUNC_SUBSCRIBE_REQ = 0x21
FUNC_SUBSCRIBE_RESP = 0x31
FUNC_POLL_REQ = 0x27
FUNC_POLL_RESP = 0x37
FUNC_TYP_REQ = 0x22
FUNC_TYP_RESP = 0x32
FUNC_HEALTH_REQ = 0x25
FUNC_HEALTH_RESP = 0x35
FUNC_PING_REQ = 0x08
FUNC_PING_RESP = 0x18
FUNC_DBSTRUCT_REQ = 0x26
FUNC_DBSTRUCT_RESP = 0x36
FUNC_ACTION_MESSAGE = 0x72

# Typicals currently supported by the public/current openHAB Souliss binding
T_EMPTY = 0x00
T_RELATED = 0xFF
T11 = 0x11
T12 = 0x12
T13 = 0x13
T14 = 0x14
T16 = 0x16
T18 = 0x18
T19 = 0x19
T1A = 0x1A
T21 = 0x21
T22 = 0x22
T31 = 0x31
T41 = 0x41
T42 = 0x42
T51 = 0x51
T52 = 0x52
T53 = 0x53
T54 = 0x54
T55 = 0x55
T56 = 0x56
T57 = 0x57
T58 = 0x58
T61 = 0x61
T62 = 0x62
T63 = 0x63
T64 = 0x64
T65 = 0x65
T66 = 0x66
T67 = 0x67
T68 = 0x68

# Known legacy/protocol constants found in the current Souliss binding source.
# There is no current native openHAB handler for these, therefore alpha.3
# preserves them as RAW diagnostics instead of guessing their semantics.
T15_LEGACY_RGB_IR = 0x15
T32_LEGACY_IR_AIRCON = 0x32

# T1n commands / feedback
T1N_TOGGLE = 0x01
T1N_ON = 0x02
T1N_OFF = 0x04
T1N_AUTO = 0x08
T1N_BRIGHT_UP = 0x10
T1N_BRIGHT_DOWN = 0x20
T1N_FLASH = 0x21
T1N_SET = 0x22
T1N_TIMED = 0x30

T1N_OFF_COIL = 0x00
T1N_ON_COIL = 0x01
T1N_OFF_COIL_AUTO = 0xF0
T1N_ON_COIL_AUTO = 0xF1
T1N_ON_FEEDBACK = 0x23
T1N_OFF_FEEDBACK = 0x24
T18_PULSE = 0xA1

# T2n commands / states
T2N_CLOSE = 0x01
T2N_OPEN = 0x02
T2N_STOP = 0x04
T2N_CLOSE_LOCAL = 0x08
T2N_OPEN_LOCAL = 0x10

T2N_COIL_OFF = 0x00
T2N_COIL_CLOSE = 0x01
T2N_COIL_OPEN = 0x02
T2N_COIL_STOP = 0x03
T2N_STATE_CLOSE = 0x08
T2N_STATE_OPEN = 0x10
T2N_LIM_CLOSE = 0x14
T2N_LIM_OPEN = 0x16
T2N_NO_LIMIT = 0x20
T2N_TIMER_OFF = 0xA0
T2N_TIMER_VAL = 0xC0
T2N_TIMEDSTOP_OFF = 0xC0
T2N_TIMEDSTOP_VAL = 0xC2

# T31 commands
T3N_AS_MEASURED = 0x03
T3N_COOLING = 0x04
T3N_HEATING = 0x05
T3N_FAN_OFF = 0x06
T3N_FAN_LOW = 0x07
T3N_FAN_MED = 0x08
T3N_FAN_HIGH = 0x09
T3N_FAN_AUTO = 0x0A
T3N_FAN_MANUAL = 0x0B
T3N_SET_TEMP = 0x0C
T3N_SHUTDOWN = 0x0D

# T41/T42 anti-theft
T4N_ALARM_INPUT = 0x01
T4N_REARM = 0x03
T4N_NOT_ARMED = 0x04
T4N_ARMED_CMD = 0x05
T4N_NO_ANTITHEFT = 0x00
T4N_ANTITHEFT = 0x01
T4N_IN_ALARM = 0x03

SUPPORTED_SWITCH_TYPICALS = {T11, T12, T18}
SUPPORTED_SENSOR_TYPICALS = {T51, T52, T53, T54, T55, T56, T57, T58}
SUPPORTED_NUMBER_TYPICALS = {T61, T62, T63, T64, T65, T66, T67, T68}

NATIVE_PLATFORM_TYPICALS = (
    SUPPORTED_SWITCH_TYPICALS
    | SUPPORTED_SENSOR_TYPICALS
    | SUPPORTED_NUMBER_TYPICALS
    | {T13, T14, T16, T19, T1A, T21, T22, T31, T41, T42}
)

TYPICAL_NAMES = {
    T11: "ON/OFF Digital Output + Timer",
    T12: "ON/OFF Digital Output + AUTO",
    T13: "Digital Input",
    T14: "Pulse Digital Output",
    T16: "RGB LED",
    T18: "ON/OFF Digital Output",
    T19: "Single Color LED",
    T1A: "8-bit Digital Input Pass Through",
    T21: "Motorized Device",
    T22: "Motorized Device + Middle Position",
    T31: "Temperature Controller",
    T41: "Anti-theft Main",
    T42: "Anti-theft Peer",
    T51: "Analog Input",
    T52: "Temperature",
    T53: "Humidity",
    T54: "Light",
    T55: "Voltage",
    T56: "Current",
    T57: "Power",
    T58: "Pressure",
    T61: "Analog Setpoint",
    T62: "Temperature Setpoint",
    T63: "Humidity Setpoint",
    T64: "Light Setpoint",
    T65: "Voltage Setpoint",
    T66: "Current Setpoint",
    T67: "Power Setpoint",
    T68: "Pressure Setpoint",
    T15_LEGACY_RGB_IR: "Legacy RGB/IR protocol constant",
    T32_LEGACY_IR_AIRCON: "Legacy IR AirCon protocol constant",
}

SERVICE_REDISCOVER = "rediscover"
SERVICE_RAW_FORCE = "raw_force"
SERVICE_TIMED = "timed"
SERVICE_RAW_MACACO = "raw_macaco"
