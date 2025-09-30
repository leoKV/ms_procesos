import io
from procesos.utils.Entry import Entry

class KFNDumper:
    TYPE_SONGTEXT = 1
    TYPE_MUSIC = 2
    TYPE_IMAGE = 3
    TYPE_FONT = 4
    TYPE_VIDEO = 5
    def __init__(self, filename: str):
        self.m_file = open(filename, "rb")
        self.inicio_digitacion = False
        self.archivo_sin_voz = False
        self.no_digitacion = 0
        self.song_ini = ""

    
    def list(self) -> list:
        files = []
        # Leer la firma inicial
        signature = self._read_bytes(4).decode("utf-8", errors="ignore")
        if signature != "KFNB":
            return []
        # Parsear los campos del encabezado (hasta encontrar "ENDH")
        while True:
            signature = self._read_bytes(4).decode("utf-8", errors="ignore")
            tipo = self._read_byte()
            len_or_value = self._read_dword()
            if tipo == 1:
                pass
            elif tipo == 2:
                _ = self._read_bytes(len_or_value)
            if signature == "ENDH":
                break
        # Leer el número de archivos en el directorio
        num_files = self._read_dword()
        # Parsear el directorio
        for _ in range(num_files):
            entry = Entry(type=0, filename="", length1=0, length2=0, offset=0, flags=0)
            filename_len = self._read_dword()
            filename_bytes = self._read_bytes(filename_len)
            entry.filename = filename_bytes.decode("utf-8", errors="ignore")
            entry.type = self._read_dword()
            entry.length1 = self._read_dword()
            entry.offset = self._read_dword()
            entry.length2 = self._read_dword()
            entry.flags = self._read_dword()
            files.append(entry)
        # Ajustar offsets con base en el final del directorio
        current_pos = self.m_file.tell()
        for entry in files:
            entry.offset += current_pos
        return files
    

    def extract_to_file(self, entry, outfilename: str):
        self.m_file.seek(entry.offset)
        try:
            with open(outfilename, "wb") as output:
                buffer_size = 8192
                total_read = 0
                while total_read < entry.length1:
                    to_read = min(buffer_size, entry.length1 - total_read)
                    data = self.m_file.read(to_read)
                    if not data:
                        break
                    output.write(data)
                    total_read += len(data)
        except OSError as e:
            print(f"Error al crear el archivo '{outfilename}': {e}")

    def extract(self, entry) -> bytes:
        self.m_file.seek(entry.offset)
        return self.m_file.read(entry.length1)

    def _read_byte(self) -> int:
        byte = self.m_file.read(1)
        if not byte:
            raise EOFError("Fin del archivo")
        return byte[0]

    def _read_dword(self) -> int:
        b1 = self._read_byte()
        b2 = self._read_byte()
        b3 = self._read_byte()
        b4 = self._read_byte()
        return (b4 << 24) | (b3 << 16) | (b2 << 8) | b1
    
    def _read_bytes(self, length: int) -> bytes:
        data = self.m_file.read(length)
        if data is None or len(data) != length:
            raise IOError("No se pudieron leer los bytes requeridos")
        return data