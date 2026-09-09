# Enclosure

The controller's shell, printed in MJF PA12, drawn around the finished board:
the board is the master dimension. `shoe.py` is the parametric FreeCAD source
for both boards' plates and shoes; `artwork.py` produces the face artwork and
the label strips; `insert_drawing.py` places the heat-set inserts. Run them
with `freecadcmd`:

```sh
freecadcmd enclosure/shoe.py      # writes enclosure/out/board-{a,b}-{plate,shoe}.stl
freecadcmd enclosure/artwork.py   # writes enclosure/out/artwork-*.{svg,png}
```

Printing waits on a measured board. The website's renders of the enclosure
are made from these outputs in the code repository, not here.
