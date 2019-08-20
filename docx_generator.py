from docx import Document


class DocxGenerator:
    def __init__(self):
        self.docx = Document()
        self.table = None

    def create_table(self, content):
        rows, cols = content.shape
        self.table = self.docx.add_table(rows= rows, cols=cols)

        for row in range(rows):
            row_cells = self.table.rows[row].cells
            for col in range(cols):
                # print(content[row][col])
                row_cells[col].text = str(content[row][col])

    def save_docx(self):
        self.docx.add_page_break()
        self.docx.save('report.docx')
