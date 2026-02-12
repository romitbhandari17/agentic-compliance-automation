"""
Local trigger for the compliance lambda handler.

Usage: run this file from the repository root with Python 3.x:

    python3 agents/compliance/trigger.py

This will call `handler(event, None)` and print the returned payload or any exception.

Note: The handler calls Amazon Bedrock via boto3; running this locally requires AWS credentials
and Bedrock access. If you don't have Bedrock access, the call may fail and you'll see the
fallback error in the printed output.
"""

import json
import traceback
from main import handler


def make_event(contract_id: str = "e0da8f55-6300-49d8-8bbc-d93ed0412bb7") -> dict:
    return {
        "contract_id": contract_id,
        "s3": {
            "bucket": "agentic-compliance-automation-dev-s3-artifacts",
            "key": "contracts/contract.pdf",
        },
        "s3_uri": "s3://agentic-compliance-automation-dev-s3-artifacts/contracts/contract.pdf",
        # extracted_text can be filled with a real sample or left empty for testing
        "extracted_text": "MASTER SERVICES AGREEMENT (MSA)\nThis Master Services Agreement (\"Agreement\") is entered into as of March 1, 2026 (\"Effective\nDate\") by and between:\n(1) Acme Analytics, Inc., a Delaware corporation with offices at 100 Market Street, San Francisco,\nCA 94105 (\"Customer\"); and\n(2) BrightVendor LLC, a New York limited liability company with offices at 200 Madison Avenue,\nNew York, NY 10016 (\"Vendor\").\n1. Services\nVendor will provide data processing and analytics services (\"Services\") as described in Statements\nof Work (\"SOWs\") executed by the parties.\n2. Term and Renewal\n2.1 Initial Term. The initial term begins on the Effective Date and continues for twelve (12) months\n(\"Initial Term\").\n2.2 Renewal. After the Initial Term, this Agreement will automatically renew for successive one (1)\nyear periods unless either party provides written notice of non-renewal at least thirty (30) days\nbefore the end of the then-current term.\n3. Fees and Payment Terms\n3.1 Fees. Customer will pay Vendor the fees set forth in the applicable SOW.\n3.2 Invoicing. Vendor will invoice monthly in arrears.\n3.3 Payment Terms. Customer will pay undisputed invoices within thirty (30) days of receipt (\"Net\n30\").\n3.4 Late Fees. Overdue amounts may accrue interest at 1.5% per month or the maximum allowed\nby law, whichever is lower.\n4. Termination\n4.1 Termination for Convenience. Customer may terminate this Agreement or any SOW for\nconvenience upon sixty (60) days' prior written notice.\n4.2 Termination for Cause. Either party may terminate this Agreement upon written notice if the\nother party materially breaches and fails to cure such breach within thirty (30) days after receiving\nwritten notice.\n4.3 Effect of Termination. Upon termination, Customer will pay Vendor for Services performed up\nto the effective date of termination.\n5. Data Protection and Confidentiality\n5.1 Confidential Information. Each party may receive confidential information from the other and\nwill protect it using at least reasonable care.\n5.2 Data Protection. Vendor will implement and maintain appropriate technical and organizational\nsecurity measures to protect Customer Data against unauthorized access, use, alteration, or\ndisclosure.\n5.3 Security Incident Notification. Vendor will notify Customer without undue delay and in any\nevent within seventy-two (72) hours after becoming aware of a confirmed security incident involving\nCustomer Data.\n5.4 Data Processing. Vendor will process Customer Data only to provide the Services and in\naccordance with Customer's documented instructions.\n6. Limitation of Liability\n6.1 Cap. Except for Excluded Claims, each party's total aggregate liability will not exceed the fees\npaid or payable in the twelve (12) months preceding the claim.\n6.2 Exclusion of Damages. Except for Excluded Claims, neither party will be liable for indirect or\nconsequential damages.\n6.3 Excluded Claims. Excluded Claims include breach of confidentiality, IP infringement, or gross\nnegligence or willful misconduct.\n7. Indemnification\n7.1 Vendor Indemnity. Vendor will indemnify Customer for third-party claims arising from IP\ninfringement or misconduct.\n7.2 Customer Indemnity. Customer will indemnify Vendor for claims arising from misuse of\nServices.\n8. Governing Law\nThis Agreement is governed by the laws of the State of New York.\n9. Miscellaneous\n9.1 Entire Agreement. This Agreement constitutes the entire agreement.\n9.2 Order of Precedence. SOWs control in case of conflict.\n9.3 Notices. Notices must be in writing by email and certified mail.\nIN WITNESS WHEREOF, the parties have executed this Agreement as of the Effective Date.\nCustomer: Acme Analytics, Inc.\nBy:\nName: Jordan Lee\nTitle: VP Procurement\nVendor: BrightVendor LLC\nBy:\nName: Taylor Morgan\nTitle: Managing Member",
    }


def main():
    event = make_event()
    print("Invoking compliance.handler with event:")
    print(json.dumps(event, indent=2))

    try:
        result = handler(event, None)
        print("\nHandler result:")
        print(json.dumps(result, indent=2))
    except Exception as e:
        print("\nHandler raised an exception:")
        print(repr(e))
        traceback.print_exc()


if __name__ == "__main__":
    main()

