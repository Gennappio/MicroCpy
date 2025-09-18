/*
Copyright 2020 Pedro Victori

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
 */
package gui;

import core.Cell;
import core.Cell3D;
import javafx.scene.*;
import javafx.scene.input.MouseEvent;
import javafx.scene.input.ScrollEvent;
import javafx.scene.shape.Box;
import twoDimCut.Panel2D;
import twoDimCut.Visualization2D;

import java.util.stream.Collectors;

import static core.SettingsProvider.SETTINGS_PROVIDER;

public class MainController3D extends MainController{
	private static final double AXIS_LENGTH = 250.0;
	private static double cameraInitialDistance = -90;
	private static final double CAMERA_INITIAL_X_ANGLE = 70.0;
	private static final double CAMERA_INITIAL_Y_ANGLE = 320.0;
	private static final double CAMERA_NEAR_CLIP = 0.1;
	private static final double CAMERA_FAR_CLIP = 10000.0;
	private final PerspectiveCamera camera = new PerspectiveCamera(true);
	private double cameraScale = 1;
	private final Xform cameraXform = new Xform();
	private final Xform cameraXform2 = new Xform();
	private final Xform cameraXform3 = new Xform();
	private double currentCameraDistance = cameraInitialDistance;
	private final Xform axisGroup = new Xform();
	private Panel2D panel2D;
	private Visualization2D visualization2D;
	private double scale2D;

	@Override
	public void initialize() {
		super.initialize();
		cameraInitialDistance *= CELL_RADIUS;
		getNodes().setDepthTest(DepthTest.ENABLE);
		buildCamera();
		buildAxes();
	}

	@Override
	protected void resize(double width) {
		super.resize(width);
		scale2D = getScale() / (currentCameraDistance / cameraInitialDistance);
		if(panel2D.isVisible()) get2DVis().setScale(scale2D);
	}

	@Override
	protected SubScene createCellsSubScene() {
		SubScene subScene = new SubScene(getNodes(), 100, 100, true, SceneAntialiasing.BALANCED);
		subScene.setCamera(camera);
		return subScene;
	}

	private void buildCamera() {
		getNodes().getChildren().add(cameraXform);
		cameraXform.getChildren().add(cameraXform2);
		cameraXform2.getChildren().add(cameraXform3);
		cameraXform3.getChildren().add(camera);
		cameraXform3.setRotateZ(180.0);

		camera.setNearClip(CAMERA_NEAR_CLIP);
		camera.setFarClip(CAMERA_FAR_CLIP);
		camera.setTranslateZ(cameraInitialDistance);
		cameraXform.ry.setAngle(CAMERA_INITIAL_Y_ANGLE);
		cameraXform.rx.setAngle(CAMERA_INITIAL_X_ANGLE);
	}

	private void buildAxes() {
		final Box xAxis = new Box(AXIS_LENGTH, 1, 1);
		final Box yAxis = new Box(1, AXIS_LENGTH, 1);
		final Box zAxis = new Box(1, 1, AXIS_LENGTH);

		xAxis.setMaterial(getPalette().getXMaterial());
		yAxis.setMaterial(getPalette().getYMaterial());
		zAxis.setMaterial(getPalette().getZMaterial());

		axisGroup.getChildren().addAll(xAxis, yAxis, zAxis);
		axisGroup.setVisible(false);
		getNodes().getChildren().addAll(axisGroup);
	}

	@Override
	protected void handleZoomSlider(double oldValue, double newValue) {
		currentCameraDistance += (newValue - oldValue) * 8;
		camera.setTranslateZ(currentCameraDistance);
	}

	@Override
	protected void handleMouseEvent(MouseEvent me, double mouseDeltaX, double mouseDeltaY) {
		double modifier = 1.;
		double rotationModifier = .5;
		double panningModifier = .2;
		double zoomModifier = .7;

		if (me.isControlDown()) {
			modifier *= CONTROL_MULTIPLIER;
		}
		if (me.isShiftDown()) {
			modifier *= SHIFT_MULTIPLIER;
		}
		if (me.isPrimaryButtonDown()) {
			cameraXform.ry.setAngle(cameraXform.ry.getAngle() - mouseDeltaX * modifier * rotationModifier);
			cameraXform.rx.setAngle(cameraXform.rx.getAngle() + mouseDeltaY * modifier * rotationModifier);
		} else if (me.isMiddleButtonDown()) {
			currentCameraDistance += mouseDeltaX * modifier * zoomModifier;
			camera.setTranslateZ(currentCameraDistance);
		} else if (me.isSecondaryButtonDown()) {
			cameraXform2.t.setX(cameraXform2.t.getX() + mouseDeltaX * modifier * panningModifier);
			cameraXform2.t.setY(cameraXform2.t.getY() + mouseDeltaY * modifier * panningModifier);
		}
	}

	@Override
	protected void handleScrollEvent(ScrollEvent event) {
		if (panel2D.isVisible() && !event.isAltDown()) { //one can still zoom when the panel is visible if alt is held down
			panel2D.move((event.getDeltaY() / 10));
		} else {
			if (event.getDeltaY() < 0) {
				getSlZoom().decrement();
			} else if (event.getDeltaY() > 0) {
				getSlZoom().increment();
			}
 		}
	}

	@Override
	protected void handleKeyboard(Scene scene) {
		scene.setOnKeyPressed(event -> {
			switch (event.getCode()) {
				case Z:
					cameraXform2.t.setX(0.0);
					cameraXform2.t.setY(0.0);
					camera.setTranslateZ(cameraInitialDistance);
					cameraXform.ry.setAngle(CAMERA_INITIAL_Y_ANGLE);
					cameraXform.rx.setAngle(CAMERA_INITIAL_X_ANGLE);
					break;
				case X:
					axisGroup.setVisible(!axisGroup.isVisible());
					break;
				case P:
					panel2D.setVisible(!panel2D.isVisible());
					get2DVis().switchActive();
					show2DVisualization(get2DVis().isActive());
					break;
			}
		});
	}

	@Override
	protected void setup() {
		super.setup();

		//panel2D
		panel2D = new Panel2D(AXIS_LENGTH);
		panel2D.setVisible(false);
		Xform panelXForm = new Xform();
		panelXForm.wrap(panel2D);
		getNodes().getChildren().add(panelXForm);
	}

	@Override
	protected void runRecurrentGuiUpdates() {
		super.runRecurrentGuiUpdates();

		//update 2D visualization
		if(get2DVis().isActive() && getWorld().getRemainingGuiUpdates() > 0)
			get2DVis().setCellList(getWorld().getTumor().getCellList().stream().map(cell -> (Cell3D) cell).collect(Collectors.toList()));

		//update camera - camera pans out as tumor grows
		int newScale = getWorld().getTumor().getTotalCount()/getWorld().getTumor().getInitialNumber();
		if (newScale > (cameraScale * 2)) {
			cameraScale = newScale;
			currentCameraDistance = camera.getTranslateZ() - (10 * cameraScale);
			camera.setTranslateZ(currentCameraDistance);

			if(panel2D.isVisible()) { //todo check resize method, possible duplicate
				scale2D = getScale() / (currentCameraDistance / cameraInitialDistance);
				get2DVis().setScale(scale2D);
			}
		}
	}

	@Override
	GraphicCell createGraphicCell(Cell cell) {
		if(cell instanceof Cell3D) {
			return new GraphicCell3D((Cell3D) cell, getPalette(), CELL_RADIUS);
		} else throw new IllegalArgumentException("Cells are not 3D");
	}

	private Visualization2D get2DVis(){
		if (visualization2D == null) {
			visualization2D = new Visualization2D(getWorld().getTumor().getCellList().stream()
					.map(cell -> (Cell3D) cell).collect(Collectors.toList()), //cast to Cell3D
					getPalette(), panel2D, 1);
		}
		return visualization2D;
	}

	private void show2DVisualization(boolean on) {
		getGraphPane().getChildren().clear();
		if(on) {
			get2DVis().setScale(scale2D);
			getGraphPane().getChildren().add(get2DVis());
		}
	}


}