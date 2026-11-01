# 挑战杯材料一键生成：make（或在仓库根目录 make competition）
# 依赖：pip install -e ".[competition]"；导出 PDF 还需要 LibreOffice（soffice）
PY ?= python
DOCX := 哨兵_挑战杯作品申报书.docx
PPTX := 哨兵_挑战杯答辩PPT.pptx

.PHONY: all figs docx pptx pdf clean

all: docx pptx

figs:
	$(PY) figs.py

docx: figs
	$(PY) gen_docx.py

pptx: figs
	$(PY) gen_ppt.py

# PDF 只用于预览和提交，不入库
pdf: all
	soffice --headless --convert-to pdf --outdir build $(DOCX) $(PPTX)

clean:
	rm -rf build __pycache__
