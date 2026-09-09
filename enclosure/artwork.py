"""Artwork for the shoes: UV-DTF transfers (white lettering, transparent, one
per top, sized to the whole top so it aligns off the edges) and the die-cut
port-strip stickers for Board A. Same frame as shoe.py: board centre, mm.

Outputs SVG (text as paths) and 600 dpi PNG into out/. Order: the transfers
as "Image Transfers", the strips as die-cut stickers, matte laminated.
"""
import os, sys
os.environ["O89_SHOE_LIB"] = "1"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["svg.fonttype"] = "path"
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch, Circle, Arc, Rectangle
import qrcode
import shoe

# the site's display face, vendored (OFL): the wordmark is Michroma there
font_manager.fontManager.addfont(os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts", "Michroma.ttf"))

MM = 1 / 25.4
# the site's own voices: Michroma for the wordmark, Helvetica Neue for the
# rest, Menlo for the mono eyebrow. And the site's own paint: the km-43
# marker green and the faint text colour come from @origin89/tokens
FONT = {"family": ["Helvetica Neue", "Arial", "DejaVu Sans"], "weight": "bold"}
FONT_BOOK = {"family": ["Helvetica Neue", "Arial", "DejaVu Sans"], "weight": "regular"}
FONT_DISPLAY = {"family": ["Michroma", "DejaVu Sans"], "weight": "regular"}
FONT_MONO = {"family": ["Menlo", "DejaVu Sans Mono"], "weight": "regular"}
FAINT = "#707b87"


def spaced(t):
    """Letter-spaced caps, the cheap way matplotlib allows: thin spaces."""
    return "\u2009".join(t)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")


def canvas(w, h):
    fig = plt.figure(figsize=(w * MM, h * MM))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(-w / 2, w / 2); ax.set_ylim(-h / 2, h / 2)
    ax.set_aspect("equal"); ax.axis("off")
    return fig, ax


def text(ax, s, x, y, size_mm, color="white", ha="center", va="center", book=False, font=None):
    # matplotlib font size is in points; cap height ~0.7 em
    ax.text(x, y, s, fontsize=size_mm / 0.7 / 0.3528, color=color, ha=ha, va=va,
            **(font if font else (FONT_BOOK if book else FONT)))


def km_badge(ax, x, y, s=1.0):
    """The km 43 road marker as the road paints it: green, white keyline,
    white figures."""
    w, h = 13 * s, 22 * s
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0,rounding_size=%g" % (1.8 * s),
                                facecolor=GREEN, edgecolor="none"))
    k = 1.1 * s
    ax.add_patch(FancyBboxPatch((x - w / 2 + k, y - h / 2 + k), w - 2 * k, h - 2 * k,
                                boxstyle="round,pad=0,rounding_size=%g" % (1.2 * s),
                                fill=False, edgecolor="white", lw=0.9 * s))
    ax.plot([x - w / 2 + 2.0 * s, x + w / 2 - 2.0 * s], [y + h / 2 - 6.4 * s] * 2, color="white", lw=0.9 * s)
    text(ax, "km", x, y + h / 2 - 3.7 * s, 3.6 * s)
    text(ax, "4", x, y - 0.6 * s, 4.8 * s)
    text(ax, "3", x, y - 6.6 * s, 4.8 * s)


def save(fig, stem):
    for ext, kw in (("svg", {}), ("png", dict(dpi=600))):
        fig.savefig(os.path.join(OUT, stem + "." + ext), transparent=True, **kw)
    # a preview on the shoe's near-black, since white on transparent shows nothing
    fig.savefig(os.path.join(OUT, stem + "-preview.png"), dpi=300, facecolor="#26282e")
    print(stem)


# The faceplate grammar is Victron's, taken as the reference: brand row,
# descriptor, one big model line, an accent bar (the site's green), then a
# spec block with thin rules. White ink, transparent, sized to the whole top.
GREEN = "#04653a"          # --color-mtq-green: the km-43 marker itself


def bt_glyph(ax, x, y, h=4.6):
    """The Bluetooth rune, drawn: spine and the two crossed diagonals."""
    u = h / 2
    w = 0.52 * u
    pts = [(0, -u), (0, u), (w, u / 2), (-w, -u / 2)], [(0, -u), (w, -u / 2), (-w, u / 2)]
    for seq in pts:
        ax.plot([x + a for a, b in seq], [y + b for a, b in seq], color="white", lw=1.7,
                solid_capstyle="round", solid_joinstyle="round")


def wifi_glyph(ax, x, y, s=1.0):
    """Wi-Fi: a dot and three arcs opening upward."""
    ax.add_patch(Circle((x, y - 1.4 * s), 0.55 * s, color="white"))
    for r in (1.5, 2.5, 3.5):
        ax.add_patch(Arc((x, y - 1.4 * s), 2 * r * s, 2 * r * s, theta1=45, theta2=135, color="white", lw=1.7))


def qr_panel(ax, x_right, y_mid, url):
    """The setup code, printed as a white tile with black modules so it scans
    on any plastic colour; an inverted white-on-dark code does not, reliably.
    The url is a plain https universal link: installed app opens (cached
    association, works offline), missing app falls through to the browser.
    Module 0.65 mm, quiet zone the spec's four modules."""
    q = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=0)
    q.add_data(url)
    q.make(fit=True)
    m = q.get_matrix()
    a = 0.65
    code = len(m) * a
    panel = code + 8 * a
    ax.add_patch(FancyBboxPatch((x_right - panel, y_mid - panel / 2), panel, panel,
                                boxstyle="round,pad=0,rounding_size=1.5",
                                facecolor="white", edgecolor="none"))
    tx, ty = x_right - 4 * a - code, y_mid + code / 2
    for r, row in enumerate(m):
        for c, dark in enumerate(row):
            if dark:
                ax.add_patch(Rectangle((tx + c * a, ty - (r + 1) * a), a, a,
                                       facecolor="black", edgecolor="none"))
    return panel


def rule(ax, x0, x1, y, lw=0.9):
    ax.plot([x0, x1], [y, y], color="white", lw=lw, solid_capstyle="butt")


def wordmark(ax, x0, y, size=7.0):
    """The site's header, in ink: the Michroma wordmark over a short bar of
    the km-43 green, the mono eyebrow under both. This was picked over a
    full destination-sign panel; the type is the hero, the green an accent."""
    text(ax, spaced("ORIGIN 89"), x0, y, size, ha="left", font=FONT_DISPLAY)
    ax.plot([x0, x0 + 34.0], [y - 8.0] * 2, color=GREEN, lw=4.5, solid_capstyle="butt")
    text(ax, "BUILT AT KM 43 FOR PLACES WHERE THE GRID ENDS", x0, y - 13.5, 1.9,
         color=FAINT, ha="left", font=FONT_MONO)


def km_mark(ax, x0, y):
    """The kilometre marker, small, bottom left, no caption; the badge is
    the credit. Board A only: B runs no code, which is its whole point."""
    km_badge(ax, x0 + 3.6, y, s=0.5)


def spec_table(ax, x0, x1, y, rows, value_size=2.6):
    """The legend grammar off the SmartSolar's plate, the reference here:
    book labels, a tick, bold values, one table. Every row sits between two
    rules. Victron rules only its LED rows, but at our scale a rule that
    starts mid-table reads as a miss, not a choice."""
    sep = x0 + 24.0
    for label, value in rows:
        rule(ax, x0, x1, y, lw=0.3)
        # rows hang from their rule by the BASELINE: a bbox centre moves
        # with descenders, so "Supply" would ride higher than "Buses" and
        # the wobble reads as doubled rules
        yb = y - 4.4
        text(ax, label, x0 + 1.0, yb, 2.6, ha="left", va="baseline", book=True)
        ax.plot([sep] * 2, [yb, yb + 2.2], color="white", lw=0.3, solid_capstyle="butt")
        text(ax, value, x0 + 26.0, yb, value_size, ha="left", va="baseline")
        y -= 6.2
    rule(ax, x0, x1, y, lw=0.3)


# Board A top transfer: the whole top as one sheet, aligned off the edges
shA = shoe.Shoe(shoe.A)
W, H = shA.ox1 - shA.ox0, shA.oy1 - shA.oy0
fig, ax = canvas(W, H)
cx, cy = (shA.ox0 + shA.ox1) / 2, (shA.oy0 + shA.oy1) / 2
def A(x, y):                      # board frame -> canvas frame
    return x - cx, y - cy
ax0, ax1 = A(-52.0, 0)[0], A(52.0, 0)[0]
wordmark(ax, ax0, A(0, 55.0)[1], size=7.0)
# one table, the way the SmartSolar prints its own: the supply and buses
# unruled on top, then the ruled LED legend under them, not a STATUS
# block floating somewhere else on the plate
spec_table(ax, ax0, ax1, A(0, 36.0)[1],
           [("Supply", "9 - 28 V DC"), ("Buses", "3x RS-485  ·  CAN  ·  2x VE.Direct  ·  1-Wire"),
            ("Slow blink", "Running"), ("Double blink", "No network"), ("Fast blink", "Error")],
           value_size=2.4)
# beside the bare light pipe, one small word: no ring (a ring demands
# sub-mm placement and shows every miss as eccentricity), no spaced-caps
# heading, just the label the legend rows explain
px, py = shoe.A["led_pipes"][0]
text(ax, "STATUS", *A(px + 6.0, py), 2.4, ha="left", book=True)
km_mark(ax, ax0, A(0, -66.0)[1])
# the footer, right to left: the setup tile flush on the rules' right edge
# (clear of the corner fillet, which only bites past x = 56), then the
# radios a breath to its left, everything on the badge's baseline
qw = qr_panel(ax, ax1, A(0, -66.0)[1], "https://origin89.com/setup")
gx, gy = ax1 - qw - 6.0 - 3.3, A(0, -66.0)[1]
bt_glyph(ax, gx - 10.0, gy, h=5.2)
wifi_glyph(ax, gx, gy + 0.2, s=1.15)
save(fig, "artwork-a-top-transfer")
plt.close(fig)

# Board B top transfer
shB = shoe.Shoe(shoe.B)
W, H = shB.ox1 - shB.ox0, shB.oy1 - shB.oy0
fig, ax = canvas(W, H)
wordmark(ax, -44.0, 32.0, size=6.0)
text(ax, spaced("GENERATOR"), -44.0, 12.0, 4.6, ha="left")
spec_table(ax, -44.0, 44.0, 7.0,
           [("Contact", "30 V DC max  ·  fused 2 A"), ("Watchdog", "4.5 s, hardware")])
save(fig, "artwork-b-top-transfer")
plt.close(fig)

# Port strips for A: black die-cut stickers, white text, one sheet, all
# horizontal. The front strip goes on the 6 mm band above its mouth. The
# side strips go ON THE LID, along its left and right margins, not on the
# wall bands: the right band does not exist (the top-exit notches for
# CN6/7/9 open that wall to the underside of the top over three of the four
# label positions), and the left mirrors the right so both read from the
# front on a wall mount. Labels sit at the connector centres, mapped from
# the board frame.
#
# Only FIELD wiring gets a label. CN14 (the RTC backup cell) is in the left
# mouth too but carries none: A-25's "external cell" means off-board, not
# outside the enclosure. The cell and its holder live inside the shoe,
# and a strip label would invite somebody to wire a battery in from the
# field. The website's render pipeline reads this table; do not retype it there.
STRIP_BANDS = {
    "front": ([("12V", None, -34.0), ("RS1", None, -21.0), ("RS2", None, -8.0),
               ("RS3", None, 5.0), ("CAN", None, 18.0), ("1W", None, 31.0)],
              "front, over the field connectors"),
    "left": ([("SEL", None, 14.0), ("SNS", None, -14.5), ("TNK", None, -28.0)],
             "lid, left margin, this end toward the back"),
    "right": ([("1W", None, 14.0), ("VED", None, 0.0), ("LNK", None, -15.5), ("VED", None, -41.5)],
              "lid, right margin, this end toward the back"),
}


def strip(ax, y_top, cells, title):
    """One band. Cells carry positions in the board frame; the strip sizes
    itself round them with a 9 mm margin each end and centres on the sheet."""
    lo = min(p for _, _, p in cells) - 9.0
    hi = max(p for _, _, p in cells) + 9.0
    length = hi - lo
    x0 = -length / 2
    ax.add_patch(FancyBboxPatch((x0, y_top - 6.0), length, 6.0, boxstyle="round,pad=0,rounding_size=1.2",
                                facecolor="#151619", edgecolor="#9aa0a6", lw=0.4))
    for main, sub, pos in cells:
        x = x0 + pos - lo
        if sub:
            text(ax, main, x, y_top - 2.2, 2.1)
            text(ax, sub, x, y_top - 4.6, 1.9)
        else:
            text(ax, main, x, y_top - 3.0, 2.6)
    text(ax, "%s  (%.0f mm)" % (title, length), x0, y_top + 1.6, 2.0, color="#9aa0a6", ha="left")

fig, ax = canvas(130, 52)
# three-character codes throughout: one size, one line, no wraps
strip(ax, 22.0, *STRIP_BANDS["front"])
strip(ax, 9.0, *STRIP_BANDS["left"])
strip(ax, -4.0, *STRIP_BANDS["right"])
text(ax, "die-cut on the grey outlines · matte laminate · white on #151619", 0, -20.0, 2.0, color="#9aa0a6")
save(fig, "artwork-a-port-strips")
plt.close(fig)
