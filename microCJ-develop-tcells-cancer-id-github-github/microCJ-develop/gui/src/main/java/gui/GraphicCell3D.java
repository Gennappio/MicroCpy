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

import core.Cell3D;
import geom.Point;
import geom.threeDim.Point3D;
import geom.twoDim.Point2D;
import javafx.scene.Node;
import javafx.scene.shape.Shape3D;
import javafx.scene.shape.Sphere;
import javafx.scene.transform.Translate;

final class GraphicCell3D extends GraphicCell{
	private Sphere node;

	GraphicCell3D(Cell3D cell, Palette palette, double radius) {
		super(cell, palette, radius);
	}

	@Override
	void createNode(double radius) {
		node = new Sphere(radius);
		node.setMaterial(getPalette().getMaterialFor(getCell().getSubpopulation().orElse(null)));
	}

	@Override
	Node getNode() {
		return node;
	}

	Shape3D getShape3D(){
		return node;
	}

	@Override
	void moveTo(Point target) {
		setLocation(target);
		if(target instanceof Point3D) {
			var location = (Point3D) target;
			Translate translation = new Translate(location.getX(), location.getY(), location.getZ());
			node.getTransforms().clear();
			node.getTransforms().addAll(translation);
		} else throw new IllegalArgumentException("Cells are not 3D");
	}

	@Override
	void setNecrotic() {
		node.setMaterial(getPalette().getNecrosisMaterial());
	}

	@Override
	Point cellLocationToGraphicLocation(Point cellLocation) {
		if(cellLocation instanceof Point3D cellLocation3D){
			double ratio = getRadius() / getCell().getRadius();
			return cellLocation3D.multiply(ratio);
		} else throw new IllegalArgumentException("Cells are not 3D");
	}
}
