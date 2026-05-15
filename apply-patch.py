#!/usr/bin/env python3
"""
apply-patch.py · Adds the 6h-sync-delay FAQ entry to the HIN Gateway Customer Hub.

Usage:
    python3 apply-patch.py index.html [-o output.html]

Inserts:
  1. New <details class="qa"> block in the migration FAQ section (#faq-migr)
  2. EN translation in FAQ_EN map
  3. EN body in FAQ_BODY_EN map
  4. FR translation in FAQ_FR map
  5. FR body in FAQ_BODY_FR map

Idempotent: running it twice does not duplicate entries.
"""

from __future__ import annotations
import argparse
import sys
from pathlib import Path


# ============================================================
# The patches
# ============================================================

DE_QUESTION = (
    'Was passiert mit Mails von Legacy-MGWs während einer '
    'Zertifikats-Rotation auf Stargate-Seite?'
)

# Patch 1 — HTML FAQ entry (German). Anchor: insert AFTER the
# "Referenzkunden mit produktivem Stargate?" details block.
HTML_NEW_DETAILS = '''        <details class="qa">
          <summary>Was passiert mit Mails von Legacy-MGWs während einer Zertifikats-Rotation auf Stargate-Seite?</summary>
          <div class="qa-body">
            <p>Bestehende MGWs synchronisieren die Zertifikate ihrer Peers periodisch — aktuell alle <strong>6 Stunden</strong>. Wenn auf Stargate-Seite ein neues Zertifikat aktiv wird und das alte invalidiert ist, kann es im Worst Case bis zu 6 Stunden dauern, bis ein Legacy-MGW das neue Zertifikat hat.</p>
            <p><strong>Auswirkung im Sync-Fenster:</strong></p>
            <ul>
              <li>Nur <strong>MGW → Stargate</strong> ist betroffen. Stargate → MGW läuft unverändert.</li>
              <li>Mails, die ein noch nicht synchronisierter MGW mit dem alten Schlüssel verschlüsselt absendet, kann Stargate nicht entschlüsseln.</li>
              <li>Diese Mails müssen vom Absender erneut zugestellt werden, sobald der MGW synchronisiert hat.</li>
            </ul>
            <p><strong>Was Customer-Support bei Meldung „Mail nicht angekommen" tun sollte:</strong></p>
            <ol>
              <li>Prüfen, ob das Sende-Datum innerhalb von 6 h nach einer Zertifikats-Aktivierung liegt.</li>
              <li>Den Absender bitten, die Mail erneut zu senden — der MGW sollte zu diesem Zeitpunkt bereits synchronisiert sein.</li>
              <li>Falls weiterhin Probleme: HIN-Support mit Zeitstempel und Absender-MGW kontaktieren.</li>
            </ol>
            <p><strong>Geplante Mitigation:</strong> Eine Verkürzung des Sync-Intervalls mit SEPPmail wird evaluiert. Voraussetzung ist, dass alle Kunden das aktuelle MGW-Update installiert haben — in der Praxis nicht kurzfristig durchsetzbar.</p>
          </div>
        </details>
'''

# Anchor for the HTML insertion — the existing "Referenzkunden" details block.
HTML_ANCHOR = '''        <details class="qa">
          <summary>Referenzkunden mit produktivem Stargate?</summary>
          <div class="qa-body">
            <p>Aktuell <strong>keine</strong> — kein Kunde ist mit dem neuen Appliance in Produktion. Das ist in der Alpha-Phase erwartbar. Produktions-Freigabe ab 18.05.2026.</p>
          </div>
        </details>'''

# Patch 2 — Entry in FAQ_EN map
EN_QUESTION = (
    'What happens to mail from legacy MGWs during a '
    'certificate rotation on the Stargate side?'
)
FAQ_EN_LINE = f"  'Referenzkunden mit produktivem Stargate?': 'Reference customers with productive Stargate?',"
FAQ_EN_NEW = (
    FAQ_EN_LINE
    + "\n  '" + DE_QUESTION + "': '" + EN_QUESTION + "',"
)

# Patch 3 — Entry in FAQ_BODY_EN map
FAQ_BODY_EN_ANCHOR = (
    "  'Referenzkunden mit produktivem Stargate?': "
    "'<p>Currently <strong>none</strong> — no customer is in production with the new appliance. "
    "This is expected in the alpha phase. Production approval from May 18, 2026.</p>',"
)

FAQ_BODY_EN_BODY = (
    "<p>Existing MGWs synchronize their peers\\' certificates periodically — "
    "currently every <strong>6 hours</strong>. When a new certificate becomes "
    "active on the Stargate side and the old one is invalidated, it can take up "
    "to 6 hours in the worst case for a legacy MGW to receive the new certificate.</p>"
    "<p><strong>Impact during the sync window:</strong></p>"
    "<ul>"
    "<li>Only <strong>MGW → Stargate</strong> is affected. Stargate → MGW operates unchanged.</li>"
    "<li>Mail that a not-yet-synchronized MGW sends encrypted with the old key "
    "cannot be decrypted by Stargate.</li>"
    "<li>These mails must be resent by the sender once their MGW has synchronized.</li>"
    "</ul>"
    "<p><strong>What customer support should do for a \"mail not delivered\" report:</strong></p>"
    "<ol>"
    "<li>Check whether the send timestamp falls within 6 hours of a certificate activation.</li>"
    "<li>Ask the sender to resend the mail — their MGW should now be synchronized.</li>"
    "<li>If the issue persists: contact HIN support with timestamp and sender MGW.</li>"
    "</ol>"
    "<p><strong>Planned mitigation:</strong> Shortening the sync interval with SEPPmail "
    "is under evaluation. Prerequisite is that all customers have installed the "
    "latest MGW update — which is not feasible short-term in practice.</p>"
)
FAQ_BODY_EN_NEW = (
    FAQ_BODY_EN_ANCHOR
    + "\n  '" + DE_QUESTION + "': '" + FAQ_BODY_EN_BODY + "',"
)

# Patch 4 — Entry in FAQ_FR map
FR_QUESTION = (
    'Que se passe-t-il avec les courriels des MGW legacy pendant '
    'une rotation de certificat côté Stargate ?'
)
FAQ_FR_ANCHOR = "  'Referenzkunden mit produktivem Stargate?': 'Y a-t-il des clients de référence avec Stargate en production ?',"
FAQ_FR_NEW = (
    FAQ_FR_ANCHOR
    + "\n  '" + DE_QUESTION + "': '" + FR_QUESTION + "',"
)

# Patch 5 — Entry in FAQ_BODY_FR map
FAQ_BODY_FR_ANCHOR = (
    "  'Referenzkunden mit produktivem Stargate?': "
    "'<p>Actuellement <strong>aucun</strong> — aucun client n\\'est en production avec la nouvelle appliance. "
    "C\\'est attendu en phase alpha. Approbation production à partir du 18 mai 2026.</p>',"
)
FAQ_BODY_FR_BODY = (
    "<p>Les MGW existants synchronisent périodiquement les certificats de leurs pairs — "
    "actuellement toutes les <strong>6 heures</strong>. Lorsqu\\'un nouveau certificat "
    "devient actif côté Stargate et que l\\'ancien est invalidé, il peut s\\'écouler "
    "jusqu\\'à 6 heures dans le pire des cas avant qu\\'un MGW legacy reçoive le nouveau certificat.</p>"
    "<p><strong>Impact pendant la fenêtre de synchronisation :</strong></p>"
    "<ul>"
    "<li>Seul <strong>MGW → Stargate</strong> est concerné. Stargate → MGW fonctionne sans changement.</li>"
    "<li>Les courriels qu\\'un MGW non encore synchronisé envoie chiffrés avec "
    "l\\'ancienne clé ne peuvent pas être déchiffrés par Stargate.</li>"
    "<li>Ces courriels doivent être renvoyés par l\\'expéditeur dès que son MGW a synchronisé.</li>"
    "</ul>"
    "<p><strong>Que doit faire le support client lors d\\'un signalement « courriel non reçu » :</strong></p>"
    "<ol>"
    "<li>Vérifier si la date d\\'envoi se situe dans les 6 h suivant une activation de certificat.</li>"
    "<li>Demander à l\\'expéditeur de renvoyer le courriel — son MGW devrait à présent être synchronisé.</li>"
    "<li>Si le problème persiste : contacter le support HIN avec l\\'horodatage et le MGW expéditeur.</li>"
    "</ol>"
    "<p><strong>Mitigation prévue :</strong> Une réduction de l\\'intervalle de synchronisation "
    "avec SEPPmail est en cours d\\'évaluation. Cela nécessite que tous les clients aient installé "
    "la dernière mise à jour MGW — ce qui n\\'est pas réalisable à court terme en pratique.</p>"
)
FAQ_BODY_FR_NEW = (
    FAQ_BODY_FR_ANCHOR
    + "\n  '" + DE_QUESTION + "': '" + FAQ_BODY_FR_BODY + "',"
)


# ============================================================
# Patcher
# ============================================================

def apply_patches(html: str) -> tuple[str, list[str]]:
    """Apply all 5 patches. Returns (modified_html, report)."""
    report: list[str] = []
    out = html

    # Idempotency check
    if DE_QUESTION in out:
        report.append('⚠  The patch appears to already be applied (German question found in file). '
                      'Skipping to avoid duplicates.')
        return out, report

    # Patch 1 — HTML FAQ block
    if HTML_ANCHOR in out:
        out = out.replace(HTML_ANCHOR, HTML_ANCHOR + '\n\n' + HTML_NEW_DETAILS, 1)
        report.append('✔  Patch 1/5 · New FAQ <details> block inserted in #faq-migr.')
    else:
        report.append('✗  Patch 1/5 FAILED · Anchor not found: '
                      '"Referenzkunden mit produktivem Stargate?" details block. '
                      'Verify your index.html version.')

    # Patch 2 — FAQ_EN entry
    if FAQ_EN_LINE in out:
        out = out.replace(FAQ_EN_LINE, FAQ_EN_NEW, 1)
        report.append('✔  Patch 2/5 · Entry added to FAQ_EN (English question).')
    else:
        report.append('✗  Patch 2/5 FAILED · Anchor not found in FAQ_EN map.')

    # Patch 3 — FAQ_BODY_EN entry
    if FAQ_BODY_EN_ANCHOR in out:
        out = out.replace(FAQ_BODY_EN_ANCHOR, FAQ_BODY_EN_NEW, 1)
        report.append('✔  Patch 3/5 · Entry added to FAQ_BODY_EN (English answer body).')
    else:
        report.append('✗  Patch 3/5 FAILED · Anchor not found in FAQ_BODY_EN map.')

    # Patch 4 — FAQ_FR entry
    if FAQ_FR_ANCHOR in out:
        out = out.replace(FAQ_FR_ANCHOR, FAQ_FR_NEW, 1)
        report.append('✔  Patch 4/5 · Entry added to FAQ_FR (French question).')
    else:
        report.append('✗  Patch 4/5 FAILED · Anchor not found in FAQ_FR map.')

    # Patch 5 — FAQ_BODY_FR entry
    if FAQ_BODY_FR_ANCHOR in out:
        out = out.replace(FAQ_BODY_FR_ANCHOR, FAQ_BODY_FR_NEW, 1)
        report.append('✔  Patch 5/5 · Entry added to FAQ_BODY_FR (French answer body).')
    else:
        report.append('✗  Patch 5/5 FAILED · Anchor not found in FAQ_BODY_FR map.')

    return out, report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('input', type=Path, help='Path to the original index.html')
    parser.add_argument('-o', '--output', type=Path,
                        help='Output file path (default: index.patched.html next to input)')
    args = parser.parse_args()

    if not args.input.is_file():
        print(f'Error: input file not found: {args.input}', file=sys.stderr)
        return 2

    output = args.output or args.input.with_name(args.input.stem + '.patched.html')

    html = args.input.read_text(encoding='utf-8')
    patched, report = apply_patches(html)

    print('\nPatch report:')
    for line in report:
        print('  ' + line)
    print()

    if any(line.startswith('✗') for line in report):
        print('One or more patches failed. Output NOT written.', file=sys.stderr)
        return 1

    output.write_text(patched, encoding='utf-8')
    print(f'✔  Patched file written to: {output}\n')
    return 0


if __name__ == '__main__':
    sys.exit(main()) 
