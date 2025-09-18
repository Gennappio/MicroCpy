package gui;
/**
 * @author Pedro Victori
 */
/*
Copyright 2019 Pedro Victori

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
 */

import core.Cell2D;
import geom.Point;
import geom.twoDim.Point2D;
import javafx.scene.Node;
import javafx.scene.paint.Color;
import javafx.scene.shape.Circle;

class GraphicCell2D extends GraphicCell {
	private static final double scaleMod = 6/ MainController.CELL_RADIUS;
	private static final double startingOffset = MainController.CELL_RADIUS * 50;
	public static final double STROKE_RATIO = 4; //relationship between node radius and width of its stroke
	private static double offset;
	private static double scale = 1;
	private static double verticalPanning;
	private static double horizontalPanning;
	private Circle node;

	GraphicCell2D(Cell2D cell, Palette palette, double radius) {
		super(cell, palette, radius);
	}

	@Override
	void createNode(double radius) {
		node = new Circle(radius * scale * scaleMod);
		Color color = getPalette().getColorFor(getCell().getSubpopulation().orElse(null));
		node.setFill(color);
		node.setStroke(Color.BLACK);
		node.setStrokeWidth(node.getRadius()/STROKE_RATIO);
	}

	@Override
	Node getNode() {
		return node;
	}

	@Override
	void moveTo(Point target) {
		setLocation(target);
		if(target instanceof Point2D location) {
			node.setCenterX((location.getX() + offset) * scale * scaleMod + horizontalPanning);
			node.setCenterY((location.getY() + offset) * scale * scaleMod + verticalPanning);

		} else throw new IllegalArgumentException("Cells are not 2D");
	}

	@Override
	void setNecrotic() {
		node.setFill(getPalette().getNecrosisColor());
	}

	void updateScale(){
		node.setRadius(getRadius() * scale * scaleMod);
		node.setStrokeWidth(node.getRadius()/STROKE_RATIO);
		moveTo(cellLocationToGraphicLocation(getCell().getLocation()));
	}

	static void addVerticalPanning(double verticalPanning) {
		GraphicCell2D.verticalPanning += verticalPanning;
	}

	static void addHorizontalPanning(double horizontalPanning) {
		GraphicCell2D.horizontalPanning += horizontalPanning;
	}

	@Override
	Point cellLocationToGraphicLocation(Point cellLocation) {
		if(cellLocation instanceof Point2D cellLocation2D){
			double ratio = getRadius() / getCell().getRadius();
			return cellLocation2D.multiply(ratio);
		} else throw new IllegalArgumentException("Cells are not 2D");
	}

	static double getScale() {
		return scale;
	}

	static void setScale(double scale) {
		GraphicCell2D.scale = scale;
		GraphicCell2D.offset = startingOffset / scale;
	}
}