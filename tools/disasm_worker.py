from elftools.elf.elffile import ELFFile
import capstone

with open(r'apk_extracted\lib\x86_64\libnative-lib.so', 'rb') as f:
    elf = ELFFile(f)
    for sec in elf.iter_sections():
        if sec['sh_addr'] <= 0x656d0 < sec['sh_addr'] + sec['sh_size']:
            sec_addr = sec['sh_addr']
            sec_data = sec.data()
            md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
            for addr in [0x656d0, 0x69230]:
                print(f"=== Disassembly at 0x{addr:x} ===")
                off = addr - sec_addr
                chunk = sec_data[off:off+256]
                for ins in md.disasm(chunk, addr):
                    print(f"  0x{ins.address:x}: {ins.mnemonic}\t{ins.op_str}")
