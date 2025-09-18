package twoDimCut;

import javafx.event.ActionEvent;
import javafx.event.EventHandler;
import javafx.scene.paint.Color;
import javafx.scene.paint.PhongMaterial;
import javafx.scene.shape.Box;

public class Panel2D extends Box {
	private EventHandler<ActionEvent> onMove;

	public Panel2D(double size) {
		super(size, 0.1, size);
		PhongMaterial material = new PhongMaterial();
		material.setDiffuseColor(Color.web("#6495ED", 0.5));
		setMaterial(material);
	}

	/**
	 * Move the panel along the vertical axis Y
	 * @param delta the difference between the old and new Y coordinate.
	 */
	public void move(double delta) {
		double current = getTranslateY();
		setTranslateY(current + delta);
		onMove.handle(new ActionEvent());
	}

	double getPos() {
		return getTranslateY();
	}

	void setOnMove(EventHandler<ActionEvent> onMove) {
		this.onMove = onMove;
	}
}
