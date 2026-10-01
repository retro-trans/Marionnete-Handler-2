"""Small checked SH-4 encoder for the VWF patch's conversion/measurement code."""
import struct


class Assembler:
    def __init__(self, address):
        self.address = address
        self.words = []
        self.labels = {}
        self.fixups = []
        self.literals = []

    @property
    def pc(self):
        return self.address + len(self.words) * 2

    def emit(self, *words):
        self.words.extend(words)

    def label(self, name):
        if name in self.labels:
            raise ValueError('Duplicate label: ' + name)
        self.labels[name] = self.pc

    def load(self, register, value):
        index = len(self.words)
        self.fixups.append(('load', index, register, value))
        self.literals.append(value)
        self.emit(0)

    def branch(self, opcode, label):
        self.fixups.append(('branch', len(self.words), opcode, label))
        self.emit(0)

    def finish(self):
        if self.pc & 3:
            self.emit(0x0009)
        locations = {}
        for value in dict.fromkeys(self.literals):
            locations[value] = self.pc
            self.emit(value & 0xffff, value >> 16)
        for kind, index, a, b in self.fixups:
            pc = self.address + index * 2
            if kind == 'load':
                displacement = locations[b] - ((pc + 4) & ~3)
                if displacement % 4 or not 0 <= displacement // 4 <= 255:
                    raise ValueError('MOV.L literal out of range')
                self.words[index] = 0xd000 | a << 8 | displacement // 4
            else:
                displacement = self.labels[b] - (pc + 4)
                low, high, mask = (-2048, 2047, 0xfff) if a in (0xa000, 0xb000) else (-128, 127, 255)
                if displacement % 2 or not low <= displacement // 2 <= high:
                    raise ValueError('Branch out of range')
                self.words[index] = a | ((displacement // 2) & mask)
        return struct.pack('<{}H'.format(len(self.words)), *self.words)


def pc_load(register, pc, target):
    displacement = target - ((pc + 4) & ~3)
    if displacement % 4 or not 0 <= displacement // 4 <= 255:
        raise ValueError('PC-relative MOV.L out of range')
    return 0xd000 | register << 8 | displacement // 4
