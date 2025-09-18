package twoDimCut;

import core.Cell;
import core.Cell3D;
import javafx.scene.paint.Color;
import javafx.scene.shape.Circle;

public class CutCell2D extends Circle {
	private Cell3D cell;
	public CutCell2D(Cell3D cell, Color color, double scale) {
		super(cell.getPoint3D().getX() * 5 * scale, //ignore y (height) coordinate
				cell.getPoint3D().getZ() * 5 * scale,
				cell.getRadius() * 5 * scale,
				color);
		this.cell = cell;
	}

	public Cell getCell() {
		return cell;
	}

	void setScale(double newScale){
		newScale *= 5;
		setCenterX(cell.getPoint3D().getX()  * newScale);
		setCenterY(cell.getPoint3D().getZ()  * newScale);
		setRadius(cell.getRadius() * newScale);
	};
}
