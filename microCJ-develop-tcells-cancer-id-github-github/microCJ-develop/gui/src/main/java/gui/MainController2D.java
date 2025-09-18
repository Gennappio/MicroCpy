/*
Copyright 2020 Pedro Victori

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
 */
package gui;

import core.Cell;
import core.Cell2D;
import javafx.scene.Scene;
import javafx.scene.SubScene;
import javafx.scene.input.MouseEvent;
import javafx.scene.input.ScrollEvent;
import javafx.scene.paint.Color;
import javafx.scene.shape.Rectangle;

public class MainController2D extends MainController {
	private double zoomFactor = 1; //from 0.1 to 4, 1 is default size
	private double zoomOffset;

	@Override
	public void initialize() {
		super.   initialize();
	}

	@Override
	protected void resize(double width) {
		super.resize(width);
		zoom(getScale());
	}

	private void zoom(double factor) {
		GraphicCell2D.setScale(factor);
		for (GraphicCell graphicCell : getGraphicCells()) {
			if (graphicCell instanceof GraphicCell2D graphicCell2D) {
				graphicCell2D.updateScale();
			}
		}
	}

	@Override
	protected SubScene createCellsSubScene() {
		getNodes().getChildren().add(0, new Rectangle(2000, 2000, Color.WHITE));
		return new SubScene(getNodes(), 100, 100);
	}

	@Override
	protected void handleZoomSlider(double oldValue, double newValue) {
		var rawValue = newValue - 50; //50 is the middle value
		zoomFactor = rawValue <= 0 ? 1 + rawValue/50 : rawValue/50 * 3 + 1;
		zoom(getScale() * zoomFactor);
	}

	@Override
	protected void handleMouseEvent(MouseEvent me, double mouseDeltaX, double mouseDeltaY) {
		if(me.isPrimaryButtonDown()){
			GraphicCell2D.addHorizontalPanning(mouseDeltaX);
			GraphicCell2D.addVerticalPanning(mouseDeltaY);
			for (GraphicCell graphicCell : getGraphicCells()) {
				if (graphicCell instanceof GraphicCell2D graphicCell2D) {
					graphicCell2D.moveTo(graphicCell2D.getCell().getLocation());
				}
			}
		}
	}

	@Override
	protected void handleScrollEvent(ScrollEvent event) {
		if (event.getDeltaY() < 0) {
			getSlZoom().decrement();
		} else if (event.getDeltaY() > 0) {
			getSlZoom().increment();
		}
	}

	@Override
	protected void handleKeyboard(Scene scene) {
		//todo implement as needed
	}

	@Override
	GraphicCell createGraphicCell(Cell cell) {
		if (cell instanceof Cell2D) {
			if(getScale() != GraphicCell2D.getScale()) GraphicCell2D.setScale(getScale() * zoomFactor);
			return new GraphicCell2D((Cell2D) cell, getPalette(), CELL_RADIUS);
		} else throw new IllegalArgumentException("Cells are not 2D");
	}
}