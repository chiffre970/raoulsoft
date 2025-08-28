import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.platypus.para import Paragraph
from typing import List
from datetime import datetime
from ..models import Event, OptimizationResult

def export_to_excel(result: OptimizationResult, events: List[Event], filename: str):
    """Export optimization results to Excel file with multiple sheets."""
    
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        # Sheet 1: Summary
        summary_data = {
            'Metric': ['Total Expected Points', 'Events with Teams', 'Events Skipped', 'Unique Swimmers'],
            'Value': [
                result.total_expected_points,
                len(result.assignments),
                len(result.events_skipped),
                len(result.swimmer_event_counts)
            ]
        }
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        # Sheet 2: Event Assignments
        assignments_data = []
        for assignment in result.assignments:
            event = assignment.event
            team = assignment.team
            strokes = event.get_strokes()
            
            for i, (swimmer, stroke) in enumerate(zip(team.swimmers, strokes)):
                assignments_data.append({
                    'Event #': event.event_number,
                    'Event Name': event.event_name,
                    'Session': event.session.value,
                    'Age Group': f"{assignment.age_group[0]}-{assignment.age_group[1]}",
                    'Position': stroke if event.stroke_type.value == "Medley" else f"Leg {i+1}",
                    'Swimmer': swimmer.name,
                    'Age': swimmer.age,
                    'Time': swimmer.get_time(stroke, event.distance),
                    'Team Time': assignment.expected_time if i == 0 else '',
                    'Expected Points': assignment.expected_points if i == 0 else ''
                })
        
        if assignments_data:
            assignments_df = pd.DataFrame(assignments_data)
            assignments_df.to_excel(writer, sheet_name='Event Assignments', index=False)
        
        # Sheet 3: Swimmer Usage
        swimmer_data = []
        for name, count in sorted(result.swimmer_event_counts.items()):
            swimmer_data.append({
                'Swimmer': name,
                'Events Assigned': count,
                'Events Remaining': 6 - count
            })
        
        if swimmer_data:
            swimmer_df = pd.DataFrame(swimmer_data)
            swimmer_df.to_excel(writer, sheet_name='Swimmer Usage', index=False)
        
        # Sheet 4: Skipped Events
        if result.events_skipped:
            skipped_data = []
            for skip in result.events_skipped:
                parts = skip.split(': ', 1)
                skipped_data.append({
                    'Event': parts[0] if len(parts) > 0 else skip,
                    'Reason': parts[1] if len(parts) > 1 else ''
                })
            
            skipped_df = pd.DataFrame(skipped_data)
            skipped_df.to_excel(writer, sheet_name='Skipped Events', index=False)
        
        # Auto-adjust column widths
        for sheet in writer.sheets.values():
            for column in sheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                sheet.column_dimensions[column_letter].width = adjusted_width

def export_to_pdf(result: OptimizationResult, events: List[Event], filename: str):
    """Export optimization results to PDF file."""
    
    doc = SimpleDocTemplate(filename, pagesize=landscape(letter))
    story = []
    styles = getSampleStyleSheet()
    
    # Title
    title = Paragraph("Relay Team Optimization Results", styles['Title'])
    story.append(title)
    story.append(Spacer(1, 0.3*inch))
    
    # Summary
    summary = Paragraph(f"<b>Total Expected Points:</b> {result.total_expected_points:.0f}<br/>"
                       f"<b>Events with Teams:</b> {len(result.assignments)}<br/>"
                       f"<b>Events Skipped:</b> {len(result.events_skipped)}<br/>"
                       f"<b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}", 
                       styles['Normal'])
    story.append(summary)
    story.append(Spacer(1, 0.3*inch))
    
    # Event Assignments
    for assignment in result.assignments:
        event = assignment.event
        team = assignment.team
        
        # Event header
        event_header = Paragraph(f"<b>Event {event.event_number}: {event.event_name}</b><br/>"
                               f"Session: {event.session.value} | "
                               f"Age Group: {assignment.age_group[0]}-{assignment.age_group[1]} | "
                               f"Expected Points: {assignment.expected_points:.0f}",
                               styles['Heading2'])
        story.append(event_header)
        story.append(Spacer(1, 0.1*inch))
        
        # Team table
        table_data = [['Position', 'Swimmer', 'Age', 'Time']]
        strokes = event.get_strokes()
        
        for i, (swimmer, stroke) in enumerate(zip(team.swimmers, strokes)):
            position = stroke if event.stroke_type.value == "Medley" else f"Leg {i+1}"
            time = swimmer.get_time(stroke, event.distance)
            time_str = format_time(time) if time else 'N/A'
            
            table_data.append([
                position,
                swimmer.name,
                str(swimmer.age),
                time_str
            ])
        
        # Add total time row
        table_data.append(['', '', 'Total:', format_time(assignment.expected_time)])
        
        table = Table(table_data, colWidths=[1.5*inch, 3*inch, 1*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ]))
        
        story.append(table)
        story.append(Spacer(1, 0.3*inch))
    
    # Swimmer Usage (new page)
    story.append(PageBreak())
    story.append(Paragraph("Swimmer Usage Summary", styles['Heading1']))
    story.append(Spacer(1, 0.2*inch))
    
    usage_data = [['Swimmer', 'Events Assigned', 'Events Remaining']]
    for name, count in sorted(result.swimmer_event_counts.items()):
        usage_data.append([name, str(count), str(6 - count)])
    
    usage_table = Table(usage_data, colWidths=[4*inch, 2*inch, 2*inch])
    usage_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(usage_table)
    
    # Skipped Events
    if result.events_skipped:
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph("Skipped Events", styles['Heading2']))
        story.append(Spacer(1, 0.1*inch))
        
        for skip in result.events_skipped:
            story.append(Paragraph(f"• {skip}", styles['Normal']))
    
    # Build PDF
    doc.build(story)

def format_time(seconds: float) -> str:
    """Format time in seconds to MM:SS.HH or SS.HH format."""
    if seconds == float('inf'):
        return "N/A"
    
    minutes = int(seconds // 60)
    seconds = seconds % 60
    
    if minutes > 0:
        return f"{minutes}:{seconds:05.2f}"
    else:
        return f"{seconds:.2f}"