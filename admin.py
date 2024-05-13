from django.contrib import admin, messages
from .models import Customer, Driver, Tanker, Supply, CustomerCategory
from rangefilter.filters import DateRangeFilterBuilder
from django.db.models import Sum
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _
from datetime import datetime

# Register your models here.


class CustomerFilter(admin.ModelAdmin):
    list_filter = ['category','active']
    search_fields = ('name',)
    list_display = ['name', 'pending_amount','category']


def mark_as_paid(modeladmin, request, queryset):
    amount_to_update = {}
    for sup in queryset:
        if sup.paid.lower() == 'no':
            if sup.customer.id not in amount_to_update:
                amount_to_update[sup.customer.id] = sup.amount
            else:
                amount_to_update[sup.customer.id] += sup.amount

    queryset.update(paid='YES')

    for key, val in amount_to_update.items():
        customer = Customer.objects.get(id=key)
        customer.pending_amount -= val
        customer.save()

mark_as_paid.short_description = "Mark selected supplies as paid"

def download_as_pdf(self, request, queryset):
    print(request)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="output.pdf"'

    # Create a PDF document
    doc = SimpleDocTemplate(response, pagesize=letter)
    elements = []

    max_d, min_d = None, None

    # Create company information
    company_info = Paragraph('<b>Company Name</b><br/>GST Number: XXXXXXXXXX', getSampleStyleSheet()["Normal"])
    elements.append(company_info)

    # Add current date


    # Create data for the table
    data = [['Customer','Date','Amount','Paid','Tanker','Driver']]

    total_pending = 0
    for obj in queryset:
        data.append([ obj.customer.name, obj.date, obj.amount, obj.paid, obj.tanker.vehicle_no, obj.driver.name]) 
        if obj.paid.lower() == 'no':
            total_pending += obj.amount

        if max_d == None or min_d == None:
            max_d = obj.date
            min_d = obj.date
        else:
            max_d = max(max_d, obj.date)
            min_d = min(min_d, obj.date)
    
    date_info = Paragraph(f'<br/>The bill is generated for dates starting from <b>{str(min_d)}</b> and <b>{str(max_d)}</b>', getSampleStyleSheet()["Normal"])
    elements.append(date_info)

    elements.append(Paragraph(f'<br/><br/>', getSampleStyleSheet()["Normal"]))
    

    # Create the table
    table = Table(data)

    # Add style to the table
    style = TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black)])

    table.setStyle(style)

    # Add table to the elements
    elements.append(table)

    total_pending_paragraph = Paragraph(f'<br/><br/><b>Total Pending Amount:</b> <b><i>{total_pending}</i></b>', getSampleStyleSheet()["Normal"])
    elements.append(total_pending_paragraph)
    

    # Add footer
    footer_info = Paragraph('<br/><br/>Contact owner for any support', getSampleStyleSheet()["Normal"])
    elements.append(Spacer(1, 20))  # Spacer to separate the table and footer
    elements.append(footer_info)

    # Build the PDF document
    doc.build(elements)

    return response

download_as_pdf.short_description = _("Download selected as PDF")

class SupplyFilter(admin.ModelAdmin):
    list_filter = [
        ('date',DateRangeFilterBuilder()),
        'paid'
    ]
    list_display = ['customer','paid','date']
    search_fields = ['customer__name']
    raw_id_fields = ('customer',)
    actions = [mark_as_paid, download_as_pdf]

    def save_model(self, request, obj, form, change):
        try:
            obj.save()
        except Exception as e:
            self.message_user(request, f"Error: {e}", level=messages.ERROR)


admin.site.register(CustomerCategory)
admin.site.register(Tanker)
admin.site.register(Driver)
admin.site.register(Supply, SupplyFilter)
admin.site.register(Customer, CustomerFilter)