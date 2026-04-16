class Esp32Protocol:
    @staticmethod
    def encode_cmd(cmd: str) -> bytes:
        return f"{cmd}\n".encode()

    @staticmethod
    def parse_status_response(lines: list) -> dict:
        result = {'speed_constant': None, 'max_rpm': None}
        for line in lines:
            line = line.strip()
            if line.startswith('SC,'):
                try:
                    result['speed_constant'] = float(line.split(',')[1])
                except (ValueError, IndexError):
                    pass
            elif line.startswith('MX,'):
                try:
                    result['max_rpm'] = float(line.split(',')[1])
                except (ValueError, IndexError):
                    pass
        return result

    @staticmethod
    def parse_data_line(line: str) -> tuple:
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

    @staticmethod
    def parse_calib_done(line: str) -> dict:
        line = line.strip()
        if line.startswith('CALIB_DONE'):
            parts = line.split(',')
            try:
                speed_constant = float(parts[1]) if len(parts) > 1 else None
                max_rpm = float(parts[2]) if len(parts) > 2 else None
                return {
                    'speed_constant': speed_constant,
                    'max_rpm': max_rpm
                }
            except (ValueError, IndexError):
                return {'speed_constant': None, 'max_rpm': None}
        return None

    @staticmethod
    def encode_char_data(pwm: int, speed: float) -> bytes:
        return f"CHAR_DATA,{pwm},{speed:.2f}\n".encode()

    @staticmethod
    def encode_char_clear() -> bytes:
        return b"CHAR_CLEAR\n"