from elftools.elf.elffile import ELFFile
import capstone

with open(r'apk_extracted\lib\x86_64\libnative-lib.so', 'rb') as f:
    elf = ELFFile(f)
    symtab = elf.get_section_by_name('.dynsym')
    sym_dict = {s['st_value']: s.name for s in symtab.iter_symbols()}
    
    # Also find PLT relocations
    rel_plt = elf.get_section_by_name('.rela.plt')
    plt_dict = {}
    if rel_plt:
        for rel in rel_plt.iter_relocations():
            sym_idx = rel['r_info_sym']
            sym = symtab.get_symbol(sym_idx)
            plt_dict[rel['r_offset']] = sym.name

    for sec in elf.iter_sections():
        if sec['sh_addr'] <= 0x6b4c0 < sec['sh_addr'] + sec['sh_size']:
            sec_addr = sec['sh_addr']
            sec_data = sec.data()
            off = 0x6b4c0 - sec_addr
            chunk = sec_data[off:off+3361]
            md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
            print("=== Disassembly of ohMyYes calls ===")
            for ins in md.disasm(chunk, 0x6b4c0):
                if ins.mnemonic == 'call':
                    target_str = ins.op_str
                    try:
                        target_addr = int(target_str, 16)
                        name = sym_dict.get(target_addr, '')
                        print(f"  0x{ins.address:x}: call 0x{target_addr:x} {name}")
                    except:
                        print(f"  0x{ins.address:x}: call {ins.op_str}")
