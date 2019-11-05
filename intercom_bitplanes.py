# Adding a buffer.

import sounddevice as sd
import numpy as np
import struct
from intercom_buffer import Intercom_buffer

if __debug__:
    import sys

class Intercom_bitplanes(Intercom_buffer):

     
    def init(self, args):
        Intercom_buffer.init(self, args)

    def run(self):

        self.recorded_chunk_number = 0
        self.played_chunk_number = 0
        self.MAX_MESSAGE_SIZE = 32768
        self.packet_format = "fffB"

        def receive_and_buffer():
            #RECIBIMOS EL MENSAJE EMPAQUETADO
            message, source_address = self.receiving_sock.recvfrom(self.MAX_MESSAGE_SIZE)
            #EXTRAEMOS LA INFORMACIÓN DEL MENSAJE RECIBIDO ANTERIORMENTE
            contenido = struct.unpack(self.packet_format, message)
            numero_chunk = contenido[0]
            bits_a_desplazar = contenido[1]
            canal = contenido[2]
            plano_de_bits = np.unpackbits(np.asarray(contenido[3], dtype=np.uint8))
            array_plano = np.asarray(plano_de_bits, dtype = np.uint16)
            array_plano_desplazado = array_plano << bits_a_desplazar
            #INSERTAMOS LA INFORMACIÓN DESEMPAQUETADA EN EL BUFFER
            self._buffer[numero_chunk % self.cells_in_buffer][:, canal] = array_plano_desplazado
            return numero_chunk

        def record_send_and_play(indata, outdata, frames, time, status):
            for i in range (16):
                for j in range (2): #cambiar 2 por self.number_of_channels
                    bits_significativos = indata[:,j] >> (15 - i)                                                   #CALCULAMOS LOS BITS MAS SIGNIFICATIVOS DE CADA CANAL
                    plano_de_bits = np.packbits(bits_significativos)                                                #CALCULAMOS EL LL PLANO DE BITS
                    message = struct.pack(self.packet_format, self.recorded_chunk_number, i, j, plano_de_bits)      #CRAEAMOS UN MENSAJE EMPAQUETADO CON LO CALCULADO ANTERIORMENTE
                    self.sending_sock.sendto(message, (self.destination_IP_addr, self.destination_port))            #ENVIAMOS EL MENSAJE EMPAQUETADO

            self.recorded_chunk_number = (self.recorded_chunk_number + 1) % self.MAX_CHUNK_NUMBER
            chunk = self._buffer[self.played_chunk_number % self.cells_in_buffer]
            self._buffer[self.played_chunk_number % self.cells_in_buffer] = self.generate_zero_chunk()
            self.played_chunk_number = (self.played_chunk_number + 1) % self.cells_in_buffer
            outdata[:] = chunk
            if __debug__:
                sys.stderr.write("."); sys.stderr.flush()

        with sd.Stream(samplerate=self.frames_per_second, blocksize=self.frames_per_chunk, dtype=np.int16, channels=self.number_of_channels, callback=record_send_and_play):
            print("-=- Press CTRL + c to quit -=-")
            first_received_chunk_number = receive_and_buffer()
            self.played_chunk_number = (first_received_chunk_number - self.chunks_to_buffer) % self.cells_in_buffer
            while True:
                receive_and_buffer()

if __name__ == "__main__":
    intercom = Intercom_bitplanes()
    parser = intercom.add_args()
    args = parser.parse_args()
    intercom.init(args)
    intercom.run()
