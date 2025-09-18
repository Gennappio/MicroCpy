module microCJ.gui {
	requires javafx.controls;
	requires javafx.fxml;
	requires microCJ.core;
	requires org.apache.commons.configuration2;
	requires java.desktop;
	requires javafx.swing;
	requires org.jgrapht.core;
	opens gui to javafx.fxml;
	exports gui;
}