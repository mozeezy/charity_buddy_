from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import utils
from reportlab.lib.utils import ImageReader
from io import BytesIO
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def generate_donation_pie_chart(donations):

    #
    cause_totals = {}
    for donation in donations:
        cause_totals[donation.cause.name] = (
            cause_totals.get(donation.cause.name, 0) + donation.amount
        )

    causes = list(cause_totals.keys())
    amounts = list(cause_totals.values())

    fig, ax = plt.subplots()
    wedges, texts, autotexts = ax.pie(
        amounts, labels=causes, autopct="%1.1f%%", startangle=90
    )
    ax.axis("equal")

    ax.legend(
        wedges, causes, title="Causes", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1)
    )

    chart_buffer = BytesIO()
    plt.savefig(chart_buffer, format="PNG", bbox_inches="tight")
    chart_buffer.seek(0)
    plt.close(fig)

    return chart_buffer


def generate_donation_bar_chart(donations):

    donations = sorted(donations, key=lambda d: d.date)

    dates = [donation.date.strftime("%Y-%m-%d") for donation in donations]
    amounts = [donation.amount for donation in donations]

    fig, ax = plt.subplots()
    ax.bar(dates, amounts, color="skyblue", label="Donation Amount")

    ax.set_xlabel("Date of Donation")
    ax.set_ylabel("Donation Amount")
    ax.set_title("Donations Over Time")
    plt.xticks(rotation=45, ha="right")

    ax.legend(loc="upper left")

    chart_buffer = BytesIO()
    plt.savefig(chart_buffer, format="PNG", bbox_inches="tight")
    chart_buffer.seek(0)
    plt.close(fig)

    return chart_buffer


def get_image(path, width=1 * inch, height=1 * inch):
    img = utils.ImageReader(path)
    iw, ih = img.getSize()
    aspect = ih / float(iw)
    return img, width, width * aspect


def generate_donor_report(donor, donations):

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    pdf.setTitle("Charity Impact Report")

    primary_color = colors.HexColor("#3498db")
    secondary_color = colors.HexColor("#2ecc71")

    pdf.setFillColor(primary_color)
    pdf.rect(0, height - 120, width, 120, fill=True, stroke=False)

    pdf.setFont("Helvetica-Bold", 36)
    pdf.setFillColor(colors.white)
    pdf.drawCentredString(width / 2, height - 80, "Charity Impact Report")

    try:
        img_path = "path_to_logo.png"
        img, img_width, img_height = get_image(img_path, width=2 * inch)
        pdf.drawImage(
            img,
            width - img_width - 50,
            height - img_height - 50,
            width=img_width,
            height=img_height,
            mask="auto",
        )
    except:
        print("Logo not found")

    pdf.setFont("Helvetica", 14)
    pdf.setFillColor(colors.black)
    pdf.drawCentredString(
        width / 2, height - 150, f"Prepared for {donor.first_name} {donor.last_name}"
    )

    pdf.line(100, height - 160, width - 100, height - 160)

    pdf.setFont("Helvetica", 12)
    pdf.drawString(100, height - 180, f"Dear {donor.first_name},")
    pdf.drawString(
        100,
        height - 200,
        "Thank you for your generous contributions. Below is a summary of your donations.",
    )

    pdf.showPage()

    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawCentredString(width / 2, height - 100, "Donation Summary")

    y_position = height - 140

    pdf.setFont("Helvetica-Bold", 12)
    pdf.setFillColor(primary_color)
    pdf.drawString(100, y_position, "Donation ID")
    pdf.drawString(250, y_position, "Cause")
    pdf.drawString(400, y_position, "Amount")
    pdf.drawString(500, y_position, "Date")

    y_position -= 20
    pdf.setFillColor(colors.black)

    for donation in donations:
        pdf.setFont("Helvetica", 12)
        pdf.drawString(100, y_position, donation.donation_id)
        pdf.drawString(250, y_position, donation.cause.name)
        pdf.drawString(400, y_position, f"${donation.amount:.2f}")
        pdf.drawString(500, y_position, donation.date.strftime("%Y-%m-%d"))

        y_position -= 40

        if y_position < 100:
            pdf.showPage()
            y_position = height - 100

    pdf.showPage()

    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawCentredString(width / 2, height - 100, "Donation Summary and Trends")

    pie_chart = generate_donation_pie_chart(donations)

    bar_chart = generate_donation_bar_chart(donations)

    chart_width = width - 100
    chart_height = 250

    pie_x = 50
    pie_y = height - 370

    pdf.drawImage(
        ImageReader(pie_chart), pie_x, pie_y, width=chart_width, height=chart_height
    )

    bar_x = 50
    bar_y = pie_y - chart_height - 70

    pdf.drawImage(
        ImageReader(bar_chart),
        bar_x,
        bar_y,
        width=chart_width,
        height=chart_height + 50,
    )

    pdf.showPage()

    pdf.setFont("Helvetica-Bold", 24)
    pdf.setFillColor(secondary_color)
    pdf.drawCentredString(width / 2, height - 100, "Thank You!")

    pdf.setFont("Helvetica", 14)
    pdf.setFillColor(colors.black)
    pdf.drawCentredString(
        width / 2, height - 140, "We appreciate your continued support."
    )
    pdf.drawCentredString(
        width / 2, height - 160, "Together, we can achieve great things."
    )

    pdf.save()

    buffer.seek(0)
    return buffer
