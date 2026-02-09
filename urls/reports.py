# reports.py - Issue reporting and viewing endpoints

from fastapi.responses import HTMLResponse
from fastapi import HTTPException
from pydantic import BaseModel
from typing import Optional
import json
import time
import logging

logger = logging.getLogger(__name__)


class IssueReport(BaseModel):
    issue_type: Optional[str] = None
    train_id: Optional[str] = None
    train_name: Optional[str] = None
    user_id: Optional[str] = "anonymous"
    timestamp: Optional[str] = None
    description: Optional[str] = None
    blue_train_position: Optional[float] = None
    gray_train_position: Optional[float] = None
    is_using_gps: Optional[bool] = False
    latitude: Optional[float] = None
    longitude: Optional[float] = None


async def report_issue_post(report: IssueReport):
    """Handle JSON issue report submissions from the app"""
    logger.info(f"\n📋 ISSUE REPORT RECEIVED:")
    logger.info(f"   Type: {report.issue_type or 'Not specified'}")
    logger.info(f"   Train: {report.train_name or 'Unknown'} ({report.train_id or 'Unknown ID'})")
    logger.info(f"   User: {report.user_id}")
    logger.info(f"   Time: {report.timestamp or 'Not specified'}")
    logger.info(f"   Description: {report.description or 'No description'}")
    
    if report.blue_train_position:
        gps_indicator = "(GPS)" if report.is_using_gps else "(System)"
        logger.info(f"   Blue Train Position: {report.blue_train_position} {gps_indicator}")
    if report.gray_train_position:
        logger.info(f"   Gray Train Position: {report.gray_train_position} (User reports)")
    
    if report.latitude is not None and report.longitude is not None:
        logger.info(f"   📍 Location: {report.latitude:.6f}, {report.longitude:.6f}")
        logger.info(f"   🗺️  Maps Link: https://maps.google.com/maps?q={report.latitude},{report.longitude}")
    elif report.latitude is not None or report.longitude is not None:
        logger.warning(f"   ⚠️  Partial location data: lat={report.latitude}, lng={report.longitude}")
    else:
        logger.info(f"   📍 Location: Not available")
    
    logger.info("   ✅ Issue report logged successfully\n")
    
    try:
        with open("issue_reports.log", "a") as f:
            f.write(json.dumps(report.model_dump()) + "\n")
    except Exception as e:
        logger.error(f"Failed to write issue report to file: {e}")
        raise HTTPException(status_code=500, detail="Failed to save report")

    return {"status": "success", "message": "Issue report received"}


async def view_reports():
    """View all issue reports in simple HTML format"""
    try:
        reports = []
        
        try:
            with open("issue_reports.log", "r") as f:
                for line in f:
                    if line.strip():
                        try:
                            report = json.loads(line.strip())
                            reports.append(report)
                        except json.JSONDecodeError:
                            continue
        except FileNotFoundError:
            pass
        
        reports.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        total_reports = len(reports)
        categorized_issues = len([r for r in reports if r.get('issue_type')])
        affected_trains = len(set(r.get('train_id', 'Unknown') for r in reports))
        unique_users = len(set(r.get('user_id', 'Anonymous') for r in reports))
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Find My BR Train - Issue Reports</title>
            <meta charset="UTF-8">
        </head>
        <body>
            <h1>🚂 Find My BR Train - Issue Reports</h1>
            
            <h2>📊 Statistics</h2>
            <ul>
                <li><strong>Total Reports:</strong> {total_reports}</li>
                <li><strong>Categorized Issues:</strong> {categorized_issues}</li>
                <li><strong>Affected Trains:</strong> {affected_trains}</li>
                <li><strong>Unique Users:</strong> {unique_users}</li>
            </ul>
            
            <h2>📋 Reports ({total_reports} total)</h2>
        """
        
        if not reports:
            html_content += "<p><em>No reports submitted yet.</em></p>"
        else:
            for i, report in enumerate(reports):
                issue_type = report.get('issue_type', 'General Issue')
                train_name = report.get('train_name', 'Unknown Train')
                train_id = report.get('train_id', 'Unknown ID')
                user_id = report.get('user_id', 'Anonymous')
                timestamp = report.get('timestamp', 'Unknown Time')
                description = report.get('description', 'No description provided')
                blue_pos = report.get('blue_train_position')
                gray_pos = report.get('gray_train_position')
                is_gps = report.get('is_using_gps', False)
                latitude = report.get('latitude')
                longitude = report.get('longitude')
                
                html_content += f"""
                <div style="border: 1px solid #ccc; margin: 10px 0; padding: 15px;">
                    <h3>#{i+1}: {issue_type}</h3>
                    <p><strong>Train:</strong> {train_name} ({train_id})</p>
                    <p><strong>Reported By:</strong> {user_id}</p>
                    <p><strong>Time:</strong> {timestamp}</p>
                    <p><strong>Description:</strong> {description}</p>
                """
                
                if blue_pos or gray_pos:
                    html_content += "<p><strong>Position Information:</strong></p><ul>"
                    if blue_pos:
                        gps_indicator = "(GPS)" if is_gps else "(System)"
                        html_content += f"<li>Blue Train Position: {blue_pos} {gps_indicator}</li>"
                    if gray_pos:
                        html_content += f"<li>Gray Train Position: {gray_pos} (User Report)</li>"
                    html_content += "</ul>"
                
                if latitude is not None and longitude is not None:
                    html_content += f"""
                    <p><strong>📍 Location Information:</strong></p>
                    <ul>
                        <li>Latitude: {latitude:.6f}</li>
                        <li>Longitude: {longitude:.6f}</li>
                        <li><a href="https://maps.google.com/maps?q={latitude},{longitude}" target="_blank">🗺️ View on Google Maps</a></li>
                        <li><a href="https://www.openstreetmap.org/?mlat={latitude}&mlon={longitude}&zoom=16" target="_blank">🗺️ View on OpenStreetMap</a></li>
                    </ul>
                    """
                elif latitude is not None or longitude is not None:
                    html_content += f"""
                    <p><strong>⚠️ Partial Location:</strong> lat={latitude}, lng={longitude}</p>
                    """
                else:
                    html_content += "<p><strong>📍 Location:</strong> Not available</p>"
                
                html_content += "</div>"
        
        html_content += f"""
            <hr>
            <p><small>Last updated: {int(time.time())} | <a href="/report">Refresh</a></small></p>
        </body>
        </html>
        """
        
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        return HTMLResponse(content=f"""
        <html>
        <body>
            <h1>Error Loading Reports</h1>
            <p>Error: {str(e)}</p>
        </body>
        </html>
        """)
