"""Create the editable Word version from REPORT.md using python-docx."""
from pathlib import Path
from urllib.parse import quote
import re
from markdown_it import MarkdownIt
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE as RT

ROOT = Path(__file__).resolve().parent.parent
REPO = 'https://github.com/dejavu-1280/ocean-filtered-retrieval-study'
OUT = ROOT/'柴叶航_22634127_海洋数据挖掘实验报告_修订版.docx'
doc = Document(ROOT/'柴叶航_22634127_海洋数据挖掘实验报告.docx')
# Preserve the supplied cover and all of its direct formatting.
first = next(p for p in doc.paragraphs if p.text.strip() == '海洋时空过滤检索中候选数量的自适应调整')
removing = False
for element in list(doc._element.body):
    if element is first._p: removing = True
    if removing and element.tag != qn('w:sectPr'):
        doc._element.body.remove(element)
section = doc.sections[0]
section.page_width, section.page_height = Inches(8.5), Inches(11)
section.top_margin = section.bottom_margin = Inches(.78)
section.left_margin = section.right_margin = Inches(.85)
section.header_distance = section.footer_distance = Inches(.35)

def set_font(style, latin='Times New Roman', chinese='宋体', size=11):
    style.font.name = latin
    style.font.size = Pt(size)
    style.font.color.rgb = RGBColor(0, 0, 0)
    style.element.get_or_add_rPr().get_or_add_rFonts().set(qn('w:eastAsia'), chinese)

normal = doc.styles['Normal']
set_font(normal)
normal.paragraph_format.line_spacing = 1.25
normal.paragraph_format.space_after = Pt(6)
normal.paragraph_format.widow_control = True
for name, size in [('Title',19),('Subtitle',13),('Heading 1',15),('Heading 2',12.5),('Heading 3',11.5)]:
    style = doc.styles[name]
    set_font(style, chinese='黑体', size=size)
    style.font.bold = name != 'Subtitle'
    style.font.italic = False
    style.paragraph_format.space_before = Pt(12 if 'Heading' in name else 0)
    style.paragraph_format.space_after = Pt(7)
    style.paragraph_format.keep_with_next = True
    # Ensure a plain black title without decorative borders.
    for border in style.element.xpath('.//w:pBdr'):
        border.getparent().remove(border)

def online(target):
    if target.startswith(('https://','http://')):
        return target
    return REPO+'/blob/main/'+quote(target, safe='/#')

def add_link(p, text, target, bold=False, italic=False):
    h = OxmlElement('w:hyperlink')
    h.set(qn('r:id'),p.part.relate_to(online(target),RT.HYPERLINK,is_external=True))
    r = OxmlElement('w:r'); props = OxmlElement('w:rPr')
    color = OxmlElement('w:color'); color.set(qn('w:val'),'175A9C'); props.append(color)
    underline=OxmlElement('w:u');underline.set(qn('w:val'),'single');props.append(underline)
    if bold: props.append(OxmlElement('w:b'))
    if italic: props.append(OxmlElement('w:i'))
    r.append(props); t=OxmlElement('w:t');t.text=text;r.append(t);h.append(r);p._p.append(h)

def inline(p, tokens):
    bold=italic=False;link=None
    for token in tokens or []:
        if token.type=='strong_open': bold=True
        elif token.type=='strong_close': bold=False
        elif token.type=='em_open': italic=True
        elif token.type=='em_close': italic=False
        elif token.type=='link_open': link=token.attrGet('href')
        elif token.type=='link_close': link=None
        elif token.type in ('softbreak','hardbreak'): p.add_run().add_break()
        elif token.type in ('text','code_inline'):
            if link: add_link(p,token.content,link,bold,italic)
            else:
                r=p.add_run(token.content);r.bold=bold;r.italic=italic
                if token.type=='code_inline': r.font.name='Consolas';r.font.size=Pt(9.5)

footer = section.footer.paragraphs[0]
footer.clear()
footer.alignment=WD_ALIGN_PARAGRAPH.CENTER
footer.add_run('第 ')
field=OxmlElement('w:fldSimple');field.set(qn('w:instr'),'PAGE');footer._p.append(field)
footer.add_run(' 页')
for r in footer.runs:r.font.size=Pt(9)

parser=MarkdownIt('commonmark').enable('table')
tokens=parser.parse((ROOT/'REPORT_REVISED.md').read_text(encoding='utf-8'))
i=0; title_seen=False; subtitle_seen=False; table_count=0
while i<len(tokens):
    token=tokens[i]
    if token.type=='heading_open':
        content=tokens[i+1].content
        if not title_seen:
            p=doc.add_paragraph(style='Title');p.paragraph_format.page_break_before=False;title_seen=True
        elif not subtitle_seen:
            p=doc.add_paragraph(style='Subtitle');subtitle_seen=True
        else:
            level=int(token.tag[1:])-1
            p=doc.add_paragraph(style=f'Heading {min(3,max(1,level))}')
        p.add_run(re.sub(r'^(\d+(?:\.\d+)*)\.\s*',r'\1 ',content))
        i+=3;continue
    if token.type=='paragraph_open':
        p=doc.add_paragraph()
        inline(p,tokens[i+1].children)
        i+=3;continue
    if token.type=='fence':
        p=doc.add_paragraph()
        p.paragraph_format.left_indent=Inches(.16)
        p.paragraph_format.line_spacing=1.05
        for n,line in enumerate(token.content.rstrip().splitlines()):
            if n:p.add_run().add_break()
            r=p.add_run(line);r.font.name='Consolas';r.font.size=Pt(9.5)
        i+=1;continue
    if token.type=='table_open':
        rows=[];current=[];j=i+1
        while tokens[j].type!='table_close':
            if tokens[j].type=='tr_open':current=[]
            if tokens[j].type=='inline':current.append(tokens[j].children)
            if tokens[j].type=='tr_close':rows.append(current)
            j+=1
        ncols=len(rows[0]);table=doc.add_table(rows=0,cols=ncols)
        table.autofit=False
        widths=([.6,6.2] if ncols==2 else [1.7,1.0,1.25,1.35,1.5] if ncols==5 else [1.0,.85,.85,.9,.9,1.15,1.15])
        for col,w in zip(table.columns,widths):col.width=Inches(w)
        for rowno,cells in enumerate(rows):
            row=table.add_row()
            cant=OxmlElement('w:cantSplit');row._tr.get_or_add_trPr().append(cant)
            if rowno==0:
                repeat=OxmlElement('w:tblHeader');row._tr.get_or_add_trPr().append(repeat)
            for colno,cell_tokens in enumerate(cells):
                cell=row.cells[colno];cell.width=Inches(widths[colno])
                tcpr=cell._tc.get_or_add_tcPr()
                margins=OxmlElement('w:tcMar')
                for side,value in [('top','80'),('bottom','80'),('left','80'),('right','80')]:
                    e=OxmlElement('w:'+side);e.set(qn('w:w'),value);e.set(qn('w:type'),'dxa');margins.append(e)
                tcpr.append(margins)
                if rowno==0:
                    shading=OxmlElement('w:shd');shading.set(qn('w:fill'),'EDEFF1');tcpr.append(shading)
                p=cell.paragraphs[0];p.paragraph_format.space_after=Pt(2);p.paragraph_format.line_spacing=1.1
                if ncols > 2 and colno > 0:
                    p.alignment=WD_ALIGN_PARAGRAPH.CENTER
                inline(p,cell_tokens)
                for r in p.runs:r.font.size=Pt(9.5);r.bold=rowno==0
        table_count+=1
        doc.add_paragraph().paragraph_format.space_after=Pt(0)
        i=j+1;continue
    i+=1

doc.core_properties.title='海洋时空过滤检索中候选数量的自适应调整'
doc.core_properties.subject='基于提前尾段缩批的补足率与候选检查成本实验报告'
doc.core_properties.author='柴叶航'
doc.core_properties.keywords='22634127 海洋数据挖掘 尾段缩批'
doc.save(OUT)
print(f'Created {OUT.name}; tables={table_count}; paragraphs={len(doc.paragraphs)}')
