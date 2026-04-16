class Esp32Protocol:
    @staticmethod
    def encode_cmd(cmd: str) -> bytes:
        """Encode command with newline suffix: "SETPOINT,100" -> b"SETPOINT,100\n" """
        return f"{cmd}\n".encode()

    @staticmethod
    def parse_status_response(lines: list) -> dict:
        """Parse STATUS response lines into dict.
        Looks for 'SC,<value>' to get speedConstant (PPR calibration).
        Returns: {'speed_constant': float}
        """
        result = {'speed_constant': None}
        for line in lines:
            line = line.strip()
            if line.startswith('SC,'):
                try:
                    result['speed_constant'] = float(line.split(',')[1])
                except (ValueError, IndexError):
                    pass
        return result

    @staticmethod
    def parse_data_line(line: str) -> tuple:
        """Parse DATA,<time>,<rpm>,<error>,<pwm> format.
        Returns: (elapsed_ms, rpm, error, pwm) or None if invalid.
        """
        line = line.strip()
        if not line.startswith('DATA,'):
            return None
        parts = line.split(',')
        if len(parts) != 5:
            return None
        try:
            elapsed_ms = int(parts[1])
            rpm = float(parts[2])
            error = float(parts[3])
            pwm = float(parts[4])
            return (elapsed_ms, rpm, error, pwm)
        except (ValueError, IndexError):
            return None
